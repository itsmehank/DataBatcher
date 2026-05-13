# US Daily Update 성능 병목 진단 보고서

> **작성일**: 2026-05-12
> **대상 스크립트**: `apps/ingest-databatcher/scripts/us_daily_update.py`
> **계측 환경**: macOS Darwin 25.4.0, Python 3.11 venv, MySQL 8 (docker `mysql-standalone-mysql`), KR 네트워크
> **계측 브랜치**: `perf/us-daily-profiling` (분석 후 삭제됨, 커밋 SHA `c5827d4`는 git reflog에 남아 있을 수 있음)

이 문서는 향후 Claude Code 세션이 **개선 작업 계획을 세우기 위한 입력 자료**다. 결론(어떻게 고칠지)이 아니라 **문제와 측정 결과**에 초점을 둔다.

---

## 1. TL;DR

- US daily 작업이 **약 6시간** 소요되는 반면 KR daily는 **1시간 미만**. 약 6배 격차.
- **935종목 샘플(top 1000) 측정 결과, wall clock의 82.5%가 FinanceDataReader의 HTTP 호출 한 곳에 집중**.
- 종목당 평균 FDR 네트워크 왕복: **322 ms** (p95 456 ms, max 806 ms).
- DB I/O, 지표 계산, 저장 루프는 합쳐도 17.5%로 사실상 무시할 수준.
- **단일 스레드 순차 처리**가 곱셈 효과로 작용 — 호출당 latency × 10,447종목 = 약 56분(이상적), 실제로는 cold run save loop와 후속 작업(us_rs, us_minervini) 포함으로 더 길어짐.

---

## 2. 배경: 현재 시스템 구조

### 2.1 KR daily vs US daily 비교

| 항목 | KR daily | US daily |
|---|---|---|
| 패키지 | `pykrx` (`stock.get_market_ohlcv`) | `FinanceDataReader` (`fdr.DataReader`) |
| 데이터 소스 | KRX 공식 엔드포인트 (국내) | Stooq/Yahoo 등 (해외) |
| 코드 위치 | `collectors/kr_stock.py:84` | `collectors/us_stock.py:206-216` (`_fetch_via_fdr`) |
| ACTIVE 심볼 수 | **3,867건** | **10,447건** (NYSE 2,747 + NASDAQ 3,861 + ETF 3,839) |
| 동시성 | 단일 스레드 순차 | 단일 스레드 순차 |
| Rate limiter | 미사용 | 미사용 |
| Fallback | 없음 | `source_strategy: fdr` (settings.yaml:30-33) — yfinance fallback 비활성 |
| Bulk 스크립트 | `bulk_update.py`: `ThreadPoolExecutor` + `--workers` 사용 | `us_bulk_update.py`: `ThreadPoolExecutor` + `--workers` 사용 |
| **Daily 스크립트** | **단일 스레드** | **단일 스레드** (← workers 인자 자체가 없음) |

**핵심 관찰**: bulk 스크립트는 양쪽 모두 병렬화돼 있지만, **daily 스크립트는 양쪽 모두 순차**다. 이유는 KR의 경우 절대 수가 적고 pykrx의 호출당 latency가 낮아 순차로도 충분했기 때문으로 추정.

### 2.2 `us_daily_update.process_symbol` 처리 흐름

종목당 다음 5단계가 순서대로 실행된다 (`apps/ingest-databatcher/scripts/us_daily_update.py:138-260`):

1. **STEP 1 (fetch)**: 최근 50일 가격을 FDR로 수집 → `collector.fetch()` 내부에서 `fdr.DataReader(symbol, start, end)` HTTP 호출
2. **STEP 1b (db_write)**: 수집한 가격을 `us_stock_prices` 테이블에 `insert_only` upsert
3. **STEP 2 (db_read_250)**: DB에서 최근 250일 가격 재로딩 (지표 계산 입력용)
4. **STEP 3a (db_read_warmup)**: warmup 기간 포함 추가 로딩
5. **STEP 3b (pipeline.run)**: SMA/EMA 등 지표 계산 (현재 `indicators_us.pipeline` 정의 기준)
6. **STEP 4 (save_loop)**: 최신일부터 역순으로 (a) `checker.is_complete` → (b) `extract_indicators_for_date` → (c) `saver.save_long(mode=insert_only)`. 이미 모든 지표가 들어있는 날을 만나면 즉시 break (idempotent early-exit).

### 2.3 Production 운영 패턴

`CLAUDE.md`의 cron 일정:
```
0 22 * * 1-5  us_index_daily_update.py --all --force
0 22 * * 1-5  us_daily_update.py --all --with-indicators
5 7  * * 2-6  us_rs_update.py --force
10 7 * * 2-6  us_minervini_update.py --days 7 --force
```

KST 22:00에 us_daily가 시작되어 익일 07:05의 us_rs까지 약 9시간 윈도우가 있다. 사용자 체감 "약 6시간"은 us_daily + us_index_daily 합산이거나 us_daily 단독일 가능성이 모두 있어, **본 보고서의 핵심은 us_daily 한 스크립트 내부 분해**다.

---

## 3. 문제 정의

> US daily 작업이 6시간 가까이 걸리는 원인이 무엇이며, 어디를 고치면 효과가 가장 큰가?

이 질문에 답하기 위해 **계측 후 실측**을 진행했다.

---

## 4. 측정 방법

### 4.1 계측 코드 (분석 후 제거됨)

`perf/us-daily-profiling` 브랜치에서 다음 두 파일을 임시 수정:

**A. `collectors/us_stock.py`**: FDR 네트워크 호출만 따로 측정
```python
# _fetch_via_fdr 내부
t_net0 = time.perf_counter()
df = fdr.DataReader(symbol, start=start_str, end=fdr_end_str)
self.last_fetch_network_sec = time.perf_counter() - t_net0
# normalize_price_frame + clip은 별도 측정
self.last_fetch_normalize_sec = ...
```
→ collector 인스턴스에 `last_fetch_network_sec`, `last_fetch_normalize_sec` 노출.

**B. `scripts/us_daily_update.py`**: `process_symbol` 5단계를 `time.perf_counter()`로 감싸 `rec` 딕셔너리에 누적, `stats: list`에 append. 종목 끝에서 한 줄 요약 출력, main 종료 시 `print_profile_summary`로 phase별 합계/평균/p50/p95/max + market별 breakdown 출력.

### 4.2 실행 명령

```bash
python apps/ingest-databatcher/scripts/us_daily_update.py \
    --all --top 1000 --with-indicators
```

- `--top 1000`: 시총 상위 1000개. 실제 처리는 935종목 (`load_us_symbols_with_details`에서 NYSE/NASDAQ/ETF 분포 적용된 후 935 반환).
- `--with-indicators`: 가격뿐 아니라 지표까지 (실제 cron과 동일 옵션).

### 4.3 측정 상의 한계 (중요)

- 측정 시점에 이미 오늘자 가격/지표가 DB에 모두 입력된 상태였음.
- 따라서 935종목 모두 STEP 4의 **early-exit가 발생** → save_loop가 종목당 평균 2회만 반복.
- **cold run(첫 daily 실행)에서는 save_loop가 종목당 ~30회 반복**되어 save_loop 시간이 약 15배 증가할 것으로 추정.
- 즉, **현재 측정치는 FDR HTTP 비중을 다소 과장**하고 있을 수 있다. cold run에서는 FDR 비중이 80% → 60~70%로 떨어질 가능성. 그러나 여전히 압도적인 최대 단일 병목.

---

## 5. 측정 결과

### 5.1 전체 요약

```
[PROFILE SUMMARY]  symbols=935  wall=364.4s
```

**935종목, wall 6분 4초.** 종목당 평균 0.39초.

### 5.2 Phase별 분해

| Phase | sum | mean | p50 | p95 | max | **share of wall** |
|---|---:|---:|---:|---:|---:|---:|
| **FDR.fetch (HTTP+normalize)** | **302.9s** | 0.324s | 0.290s | 0.458s | 0.808s | **83.1%** |
| ↳ FDR.DataReader (network only) | **300.7s** | 0.322s | 0.288s | 0.456s | 0.806s | **82.5%** |
| ↳ normalize+clip | 1.9s | 0.002s | 0.002s | 0.003s | 0.006s | 0.5% |
| DB write (insert_only prices) | 8.7s | 0.009s | 0.010s | 0.012s | 0.016s | 2.4% |
| DB read 250d | 4.2s | 0.005s | 0.005s | 0.006s | 0.009s | 1.2% |
| DB read warmup | 4.7s | 0.005s | 0.005s | 0.007s | 0.011s | 1.3% |
| Indicator pipeline.run | 0.3s | 0.000s | 0.000s | 0.000s | 0.001s | 0.1% |
| Save loop (전체 날짜) | 22.3s | 0.024s | 0.024s | 0.029s | 0.053s | 6.1% |
| ↳ checker.is_complete | 4.4s | 0.005s | 0.005s | 0.006s | 0.011s | 1.2% |
| ↳ extract_indicators_for_date | 10.6s | 0.011s | 0.012s | 0.013s | 0.041s | 2.9% |
| ↳ saver.save_long | 7.3s | 0.008s | 0.008s | 0.010s | 0.021s | 2.0% |
| **TOTAL per symbol** | 344.2s | 0.368s | 0.336s | 0.504s | 0.847s | 94.4% |

> wall(364.4s) - TOTAL(344.2s) = 20.2s는 종목 간 부수 코드(로깅, 루프 오버헤드 등)다.

### 5.3 Market별 breakdown (평균/종목)

| Market | n | fetch | fetch_net | db_read | pipe | save | total |
|---|---:|---:|---:|---:|---:|---:|---:|
| NYSE | 243 | 0.337s | 0.334s | 0.010s | 0.000s | 0.024s | 0.381s |
| NASDAQ | 435 | 0.318s | 0.316s | 0.010s | 0.000s | 0.024s | 0.362s |
| ETF | 257 | 0.321s | 0.319s | 0.009s | 0.000s | 0.024s | 0.365s |

→ **시장별 유의미한 차이 없음.** NYSE가 ~5% 느린 정도. ETF가 별도 hot spot이 아니라는 점은 의외였음.

### 5.4 기타

- Skipped: 0 (DB에 가격이 없거나 warmup 부족으로 건너뛴 종목 없음)
- Early-exit: 935 / 935 (전수)
- FDR 호출 실패/타임아웃: 측정 구간 내 0건

---

## 6. 원인 분석

### 6.1 왜 FDR HTTP가 이렇게 큰 비중을 차지하나

- FDR의 US 종목 경로는 내부적으로 **Stooq 또는 Yahoo Finance**의 차트 엔드포인트에 HTTPS 요청을 보낸다.
- KR에서 미국 서버까지의 RTT는 보통 150~250ms. TLS handshake 포함 첫 요청은 더 큼.
- 종목당 평균 322ms는 RTT × 2~3회(연결 수립 + 본문 송수신) + 서버 처리 시간으로 설명 가능.
- pykrx의 KRX 직결 호출은 RTT 20~50ms 수준이라 호출당 latency가 6~10배 차이.

### 6.2 왜 단일 스레드가 곱셈 효과를 낳나

- 종목별 처리는 **완전히 독립적**(공유 상태 없음, 순서 의존성 없음).
- 그럼에도 `for sym_info in symbols` 단순 루프 (`us_daily_update.py:337`).
- HTTP 응답을 기다리는 동안 CPU는 전부 idle. 평균 322ms 중 대부분이 네트워크 wait.
- → **I/O bound + 독립 작업 = 병렬화의 교과서 케이스**인데 현재는 활용 안 됨.
- 참고로 `us_bulk_update.py:212`는 `ThreadPoolExecutor(max_workers=workers)` 사용 중. 동일 패턴 적용 가능.

### 6.3 6시간 추정치의 분해 (대략)

| 시나리오 | 계산 | 예상 시간 |
|---|---|---|
| 측정 그대로 외삽 (early-exit 상태, 10,447종목) | `364.4 × 10447/935` | **약 68분** |
| Cold run save_loop 보정 (save_loop만 15배 가정) | `+ 22.3 × 15 × 10447/935` | **+ 약 56분 → 약 124분 (2시간)** |
| FDR 일부 실패/재시도 (변동) | + α | 변동 |
| us_index_daily_update + 후속 작업 | + 별도 측정 필요 | 변동 |

→ **단일 us_daily만으로는 2~2.5시간이 상한**으로 예상되며, 사용자 체감 "6시간"에는 us_index_daily + 일부 환경 요인(네트워크 야간 혼잡 등)이 포함됐을 가능성이 있다. 본 보고서 범위는 us_daily 한 스크립트로 한정.

### 6.4 무시해도 되는 항목

다음은 합쳐도 11.7%이며, 손대도 체감 변화가 없으므로 **개선 대상에서 제외**해도 무방:
- pipeline.run (0.1%)
- normalize+clip (0.5%)
- DB read 250d / warmup (2.5%)
- DB write (2.4%)
- save_loop의 하위 phase 각각 (1~3%)

---

## 7. 해결 방안 후보 (계획 수립용 옵션)

> 아래는 **선택지의 목록**이지 추천 결정이 아니다. 향후 계획 세션에서 트레이드오프를 보고 결정.

### 옵션 A. **ThreadPoolExecutor 병렬화** (us_bulk_update 패턴 이식)

- **방식**: `us_daily_update.py`에 `--workers N` 인자 추가, 종목 루프를 `ThreadPoolExecutor(max_workers=N)`로 감싸 `process_symbol`을 future로 제출.
- **예상 효과**: FDR 호출이 IO-bound이므로 GIL 영향 적음. workers=4 → 4배 단축 (FDR 305s → ~75s), workers=8 → 6~7배 단축.
- **장점**: us_bulk_update에 검증된 패턴이 이미 있어 코드 이식이 단순. 자료원 그대로 유지.
- **위험**:
  - **FDR backend(Stooq/Yahoo)의 rate limit**: 동시 8 연결로 throttle/IP 차단 가능성. 보수적으로 시작(workers=4)하고 모니터링 필요.
  - DBManager engine은 pool_size 기반이므로 workers × (DB read 2회 + write 2회)가 pool_size 이하인지 확인. settings.yaml의 `database.pool_size`/`max_overflow` 점검.
  - 종목별 로그 출력 순서가 섞임 (별 영향 없지만 로그 grep 시 주의).
  - 에러 처리: 개별 종목 실패가 풀 전체를 죽이지 않도록 try/except 유지 (`us_bulk_update.py:225` 참조).
- **검증**: `--top 200 --workers 1` vs `--workers 4` vs `--workers 8` 동일 wall 비교, DB 적재 row 수 동일 확인.

### 옵션 B. **자료원 교체 — yfinance batch download**

- **방식**: `yf.download(['AAPL','MSFT', ...], start, end)`은 multi-symbol을 단일 HTTP로 받음. 100종목씩 묶으면 호출 수가 ~100배 줄어듦.
- **예상 효과**: 호출당 latency는 비슷하지만 호출 수가 100~200분의 1. 이론상 가장 큰 절감.
- **장점**: 병렬화와 직교적 (두 방안 병행 가능).
- **위험**:
  - yfinance는 응답 안정성이 변동적임 (multi-index 컬럼, 일부 ticker 누락, 가끔 빈 응답). `us_stock.py:174-196`의 `_is_valid_yfinance_response`는 단일 ticker 가정에 가까워, batch 응답용 검증 로직 신규 작성 필요.
  - 일부 ticker가 batch에서 빠질 때 fallback(개별 재요청) 처리 설계 필요.
  - 데이터 동등성: FDR(Stooq 우선) vs yfinance 종가가 가끔 다름. 기존 DB와 일관성 보장 위해 비교 검증 필요.
  - 현재 `settings.yaml`은 `source_strategy: fdr`로 고정. fallback 전략 `fdr_then_yfinance`도 존재하므로 인프라는 일부 깔려 있음.
- **검증**: 작은 그룹으로 batch fetch → 기존 DB와 종가 차이 분포 확인, 누락 종목 비율 확인.

### 옵션 C. **Stooq 직접 다운로드 (bulk CSV)**

- **방식**: stooq.com은 일별 전체 마켓 CSV를 한 번에 다운받을 수 있는 엔드포인트가 있음 (예: `https://stooq.com/db/d/`). FDR이 내부적으로 이걸 사용하기도 함.
- **예상 효과**: 호출 1회 → 수천 종목. 극적인 절감.
- **위험**:
  - 인증/약관/요청 빈도 제한 확인 필요.
  - 컬럼/심볼 매핑이 FDR 응답과 다를 수 있어 normalize 로직 신규.
  - 의존 제3자 인프라가 늘어 운영 복잡도 증가.
- **검증**: 별도 probe 스크립트(`apps/ingest-databatcher/scripts/probes/`)에 추가하여 단발성 검증.

### 옵션 D. **하이브리드: 일중 가격은 yfinance batch, 종가 확정은 FDR로 백필**

- **방식**: daily 시점에는 yfinance batch로 빠르게 채우고, 야간/주말 별도 작업에서 FDR로 덮어쓰기/검증.
- **예상 효과**: daily 실행 시간 극적 단축 + 데이터 신뢰도 유지.
- **위험**: 두 자료원의 운영을 동시 관리해야 함. 복잡도 증가.

### 옵션 E. **현 자료원 유지 + 캐시/조건부 호출**

- **방식**: 종목별 마지막 가격 날짜를 DB에서 미리 한 번에 읽어, 이미 최신인 종목은 FDR 호출 자체를 생략 (early-exit를 fetch 이전에 수행).
- **예상 효과**: 이미 데이터가 있는 종목의 FDR 호출 0회. cold run에는 효과 없음, warm run(이미 채워진 상태) 재실행 시 큰 절감.
- **장점**: 자료원 변경 없고 위험 낮음.
- **위험**: 실제 production daily는 항상 cold(=새 데이터)이므로 효과가 제한적. 측정상 935종목 모두 early-exit였던 건 "측정 시점이 이미 입력된 뒤"였기 때문.

### 옵션 F. **무대응 (현 상태 유지)**

- 6시간 윈도우(KST 22:00 us_daily → 익일 07:05 us_rs) 내에 끝나면 비즈니스적으로 무해할 수 있음.
- 그러나 향후 종목 수가 늘어나면 마진이 사라짐. 또한 일시적 FDR 장애에 대한 retry 여유도 줄어듦.

---

## 8. 우선순위 제안 (참고 의견)

(이 섹션은 결정이 아니며, 향후 계획 세션에서 사용자가 다시 판단할 영역.)

1. **옵션 A 먼저 (저비용·고효과·저위험)**. workers=4부터 시작해서 8까지 단계적으로 올리면서 안정성/throttle 모니터링.
2. A로 1시간 이내에 들어오면 거기서 종료. 아직 부족하면 **옵션 B 추가 검토** (자료원 다양화는 별도 안정성 작업이 동반되므로 단독 변경은 신중).
3. 옵션 C/D는 데이터 정합성 검증 비용이 커서 보류 추천.
4. 옵션 E는 cold run에 효과 없어 단독으로는 비추천. 다만 A 구현 시 종목별 "마지막 가격 날짜 사전 체크"를 옵션으로 넣으면 재실행 시간을 줄일 수 있음.

---

## 9. 향후 작업 시 참고사항

### 9.1 재현 방법

1. 위 4.1의 계측 패치를 다시 적용 (또는 git reflog에서 SHA `c5827d4` 복구 시도).
2. `python apps/ingest-databatcher/scripts/us_daily_update.py --all --top N --with-indicators`로 실행.
3. **콜드 데이터 측정이 필요하면** 사전에 일부 종목의 `us_stock_indicators` 최근 행을 삭제하여 early-exit를 막아야 한다. 예: `scripts/table_manipulate/manage_table.py delete-rows --table us_stock_indicators --symbol AAPL ...`.

### 9.2 측정 시 주의사항

- **이 측정은 idempotent 상태(early-exit 전수)** 였음. 첫 daily(cold) 측정에는 save_loop 비중을 별도 확인.
- DB 컨테이너(`mysql-standalone-mysql`)가 같은 호스트에 있어 DB I/O는 극도로 빠름. **DB가 별도 호스트라면** db_read/write phase 비중이 커질 수 있음.
- 측정 시점의 네트워크 상태가 결과에 영향. 야간 운영 시간(KST 22시)과 낮 시간대의 FDR latency가 다를 수 있음.

### 9.3 영향 받는 다른 스크립트

- 같은 패턴이 다음 daily 스크립트에도 존재 (병렬화 미적용):
  - `scripts/us_index_daily_update.py` (US 인덱스 — 종목 수 적어 비중 작을 것)
  - `scripts/crypto_daily_update.py` (Binance API — 자체 rate limit 있음, 별도 분석 필요)
- US 인덱스는 종목 수가 매우 적어 우선 순위 낮음.

### 9.4 거버넌스 (`CLAUDE.md` 참조)

- 본 보고서는 `_meta/` 외부의 일반 문서이므로 Builder가 자유롭게 작성/수정 가능.
- 실제 코드 수정으로 이어질 때는 Phase 단위 작업인지 확인하고, `_meta/06_CURRENT_STATE.md`와의 정합성을 점검할 것.
- daily 스크립트 변경은 `core.indicator_checker`, `core.price_loader`, `savers.indicator_saver`의 thread-safety 검토가 필요.

### 9.5 측정 결과 원본

- 로그 파일은 분석 후 사용자 요청으로 삭제됨 (`apps/ingest-databatcher/logs/profile_us_daily_top1000_20260512_181223.log`, 323KB, 3902 lines).
- 핵심 수치는 본 보고서 §5에 모두 옮겨져 있음.

---

## 10. 부록: KR 측 비교 데이터 부재

- 사용자 요청에 따라 KR daily는 동일 계측을 수행하지 않았음.
- KR이 1시간 미만으로 끝난다는 사용자 진술 + ACTIVE 3,867종목 + pykrx 호출당 latency가 FDR보다 낮다는 일반 지식만으로 본 보고서는 작성됨.
- 만약 정확한 호출당 latency 비교가 필요해지면, KR 측에도 동일한 phase 계측을 1회 추가해 호출당 평균을 얻어야 한다 (코드 패치 위치는 `collectors/kr_stock.py:84`, `scripts/daily_update.py:314` 근처).

---

**문서 끝.** 본 문서를 기반으로 한 구현 계획은 별도 문서(예: `apps/ingest-databatcher/plans/us_daily_parallelization_plan.md`)로 분리해 작성하기를 권장.
