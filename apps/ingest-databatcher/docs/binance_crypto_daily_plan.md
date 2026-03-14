# Binance 코인(Spot/USDT) 일봉 적재 기능 추가 계획서 (거시→상세)

**문서 목적**
- 현재 DataBatcher의 “일봉 적재 파이프라인(symbol_master → prices → indicators)”과 동일한 운영 경험을 유지하면서
  Binance Spot 데이터를 **코인 전용 테이블**로 적재하는 기능을 추가하기 위한 실행 가능한 계획을 제공한다.
- 이번 범위는 **일봉(1d) 수집/적재 + 일봉 지표(SMA 5/20/40) 적재**까지 포함한다.
- 주봉(1w) 확장은 **Phase 2**로 계획만 포함(이번 구현 범위 제외).

---

## 0) 결정사항 반영(사용자 확정)

1) 목표/범위 고정
- Binance **Spot** 기준
- **USDT 마켓만** (예: BTCUSDT, ETHUSDT)
- **1d(일봉)** 데이터 수집
- 캔들 기준 시간: **UTC** (일봉 date는 UTC 날짜 기준으로 저장)
- 거래량(volume): **Quote volume** 사용 (USDT 거래대금 성격)

2) 스키마 전략
- **코인 전용 테이블 추가** (주식/ETF 테이블과 분리)

3) 지표
- 코인도 주식처럼 settings에서 별도 섹션으로 관리
- 기본 일봉 지표: **SMA(5), SMA(20), SMA(40)**

4) 주봉 확장
- Phase 2에서 Binance의 **주봉 제공 API(1w klines)**를 사용해 별도 구현

---

## 1) 전체 아키텍처(현재 프로젝트 스타일 유지)

### 1.1. 파이프라인(코인)

```
Binance(Spot) → collectors/crypto_binance.py → DB: crypto_prices_daily
                                    └→ indicators/pipeline.py → DB: crypto_indicators_daily

심볼 목록: Binance exchangeInfo → scripts/crypto_sync_symbol_master.py → DB: crypto_symbol_master
```

### 1.2. 주식 파이프라인과의 관계
- 주식/ETF는 기존대로 `symbol_master`, `stock_prices`, `stock_indicators` 사용
- 코인은 전용 테이블로 분리하여 **기존 주식 파이프라인에 최소 영향**
- 공통 재사용:
  - `IndicatorPipeline`, `IndicatorSaver`, `DBManager`, `RateLimiter`(있다면) 등

---

## 2) 데이터 모델/스키마 설계(Phase 1)

> 목표: 코인 데이터를 주식과 섞지 않고, 스키마/쿼리/운영 규칙을 명확히 분리한다.

### 2.1. 신규 테이블: `crypto_symbol_master`
**목적**: 코인(거래쌍) 목록을 주기적으로 동기화

권장 컬럼(초안)
- `symbol` (PK) : 예: `BTCUSDT`
- `base_asset` : `BTC`
- `quote_asset` : `USDT`
- `status` : `ACTIVE`/`INACTIVE`
- `exchange` : `BINANCE`
- `etl_loaded_at` : timestamp

인덱스 제안
- `(quote_asset, status)`

### 2.2. 신규 테이블: `crypto_prices_daily`
**목적**: Binance 1d OHLCV 저장(UTC date)

권장 컬럼(초안)
- `symbol` (PK part)
- `date` (PK part) : DATE(UTC 기준)
- `open`, `high`, `low`, `close` : DECIMAL
- `volume_quote` : DECIMAL (quote asset volume)
- `exchange` : `BINANCE`
- `source` : `binance`
- `etl_loaded_at`

PK
- `(symbol, date)`

인덱스
- `(date)`, `(symbol, date)`

### 2.3. 신규 테이블: `crypto_indicators_daily`
**목적**: long-form 지표 저장 (주식과 동일한 롱 포맷)

권장 컬럼(초안)
- `symbol` (PK part)
- `date` (PK part)
- `indicator` (PK part) : 예 `sma_5_close`
- `params_hash` (PK part)
- `value` : DECIMAL(28,10) nullable
- `exchange` : `BINANCE`
- `source` : `binance`
- `etl_loaded_at`

PK
- `(symbol, date, indicator, params_hash)`

인덱스
- `(indicator, date)`, `(symbol, date)`

### 2.4. 마이그레이션/초기화 방식
- `scripts/init_db.py` 또는 `scripts/migrations/` 스타일에 맞춰 추가
- 기존 주식 테이블과 충돌 없도록 별도 create 구문 추가

---

## 3) 설정(config) 설계

### 3.1. `config/settings.yaml` 확장(제안)
주식이 `indicators`, `indicators_weekly`를 쓰는 것처럼 코인도 별도 섹션을 둔다.

#### 3.1.1. 코인 적재 대상 심볼 결정 규칙(최신)
코인 bulk/daily 스크립트는 아래 우선순위로 **처리 대상 심볼**을 결정한다.

1. `--all` 지정 시: `crypto_symbol_master`의 `status='ACTIVE'` 전체
2. `--symbols ...` 지정 시: 해당 심볼만
3. 위 둘 다 없으면: `config/settings.yaml`의 `crypto.targets.symbols`

3번까지 갔는데도 대상이 비어 있으면(미설정) 에러로 종료한다.

```yaml
crypto:
  exchange: BINANCE
  quote_asset: USDT
  timezone: UTC
  targets:
    # bulk/daily에서 --all/--symbols가 없을 때 기본으로 처리할 심볼 목록
    # 예: [BTCUSDT, ETHUSDT]
    symbols: [BTCUSDT]

indicators_crypto_daily:
  materialization:
    mode: long
    table_long: crypto_indicators_daily
  pipeline:
    - name: sma
      params: { window: 5, column: close }
      save: true
    - name: sma
      params: { window: 20, column: close }
      save: true
    - name: sma
      params: { window: 40, column: close }
      save: true
```

> 주의: `volume_quote`를 사용할 지표는 추후 추가(이번 기본 SMA는 close 기반)

---

## 4) 수집 로직 설계 (Collector)

### 4.1. 신규 Collector: `collectors/crypto_binance.py`
**역할**
- Binance REST API로 1d klines 조회
- 기간(start/end) 기반 페이징
- API/네트워크 예외 처리(재시도/백오프)
- 결과를 표준 DF로 반환 (date=UTC DATE, OHLC, volume_quote)

**API 후보**
- `GET /api/v3/exchangeInfo` : 심볼 목록
- `GET /api/v3/klines` : 캔들(1d)

**데이터 변환 규칙**
- Binance kline openTime(ms) → UTC date
- volume:
  - kline의 `quoteAssetVolume`을 `volume_quote`로 저장

**레이트 리밋**
- Binance weight 제한이 있으므로:
  - 기존 `core/rate_limiter.py`가 있다면 재사용
  - 없다면 최소 구현(초당 호출 제한 + 429 처리)

---

## 5) 스크립트(실행 진입점) 설계

### 5.1. 심볼 동기화: `scripts/crypto_sync_symbol_master.py`
- exchangeInfo 조회
- 조건: Spot + status=TRADING + quoteAsset=USDT
- `crypto_symbol_master`에 upsert(또는 insert_only + status 갱신)

CLI(초안)
- `--all` 고정(USDT 전체)
- `--symbols BTCUSDT ETHUSDT` 지원(테스트용)

### 5.2. Bulk 적재: `scripts/crypto_bulk_update_daily.py`
- 기간 전체 적재 + 지표 계산 + 저장

CLI(초안)
- `--start YYYY-MM-DD` (UTC date)
- `--end YYYY-MM-DD` (UTC date)
- `--all` 또는 `--symbols ...`
- `--workers N` (선택: 심볼 병렬)
- 저장 정책:
  - prices: insert_only 권장(멱등성)
  - indicators: insert_only 권장(멱등성)

### 5.3. Daily 업데이트: `scripts/crypto_daily_update.py`
- 최근 N일만 가격 갱신(예: 10~30일) + warmup 포함 지표 계산
-
-**목적**: 최근 기간(고정)만 가격/지표를 갱신
+
+현재 구현(최신)
+- 최근 **50일** 범위(고정)
+- 기본 end date: 실행 시점 UTC 날짜 기준 "어제" (완결된 일봉만 적재)
+- 필요 시 `--end YYYY-MM-DD`로 end date(UTC date)를 직접 지정
+
+CLI(최신)
+- `--all` 또는 `--symbols ...`
+- `--end YYYY-MM-DD` (선택)
+- `--with-indicators` (선택)
+- 저장 정책: prices/indicators 모두 insert_only

---

## 6) 지표 계산 로직 설계

### 6.1. 재사용
- `indicators/common/sma.py`를 그대로 사용
  - 거래일 캘린더가 아니라 단순 rolling 기반이므로 코인에도 자연스럽게 동작

### 6.2. 데이터 준비
- 입력 DF index는 UTC 일봉 date를 DatetimeIndex로 설정
- 컬럼: close 필수

### 6.3. NULL/NaN 저장 정책
- 주식에서 논의했던 것처럼, 코인도 "계산 불가(warmup 부족)"을 NULL로 저장할지 결정 필요
- 이번 계획(추천):
  - `keep_nan=True`로 row를 만들고 `value`는 NULL 저장 (멱등/완료체크에 유리)

---

## 7) 테스트/검증 계획(Phase 1)

> ⚠️ 중요(사용자 요청 반영)
> - 테스트는 항상 **(A) 테스트 실행 → (B) DB에 적재되었는지 확인 → (C) 다음 테스트 전 테스트 데이터 삭제** 순서로 진행한다.
> - **DB 확인/삭제는 SQL을 직접 콘솔에서 치지 않고**, `scripts/tests/` 아래에 만드는 “DB 확인/삭제 전용 파이썬 스크립트”로 수행한다.
> - Copilot은 터미널에서 실행/출력 확인을 직접 하지 않는다. 아래에 제시된 실행 커맨드를 사용자가 실행하고, **출력 결과를 그대로 첨부**한다.

### 7.0. 테스트에서 사용할 공통 규칙(필수)

#### 테스트 심볼(고정)
- 기본 테스트는 항상 심볼 1개로 시작: `BTCUSDT`
- 추가로 2개 심볼 테스트: `BTCUSDT`, `ETHUSDT`

#### 테스트 기간(UTC date)
- 단기간 테스트(추천): 최근 30일
- 예시(문서 작성 시점 기준): `--start 2026-01-01 --end 2026-01-31`
  - 실제 실행 시점에 맞게 사용자가 적절히 조정

#### 정리(삭제) 원칙
- 테스트는 운영 DB에서도 수행 가능하나, **테스트로 넣은 데이터는 반드시 삭제하고 다음 테스트로 넘어간다.**
- 삭제는 반드시 심볼+기간 조건을 걸어서 수행한다.

### 7.1. 오프라인 단위 테스트(네트워크/DB 없이)

목표: Binance 응답 파싱/UTC date 변환/quote volume 매핑이 코드 수준에서 올바른지 확인

#### (T1) exchangeInfo 파싱 테스트
- 파일(테스트): `scripts/tests/test_crypto_binance_exchangeinfo_parse.py`
- 내용:
  - exchangeInfo 샘플 JSON을 하드코딩(또는 fixture 파일)하고,
  - `spot + TRADING + quoteAsset=USDT`만 필터링되는지 확인
  - 출력: 선별된 심볼 개수, 5개 샘플 출력

#### (T2) klines(1d) 파싱 테스트
- 파일(테스트): `scripts/tests/test_crypto_binance_klines_parse.py`
- 내용:
  - klines 응답 샘플(JSON list)을 하드코딩
  - openTime(ms) → UTC date 변환이 정확한지
  - quoteAssetVolume 매핑이 `volume_quote`로 들어가는지
  - 출력: 변환된 DF head, dtype 요약

> 오프라인 테스트는 DB 정리 단계가 필요 없다.

### 7.2. 통합 테스트(실DB) — “적재 확인 + 삭제” 포함

#### 공통: DB 확인/삭제 스크립트(필수)
아래 스크립트들은 “테스트 실행 후 적재 확인”과 “다음 테스트 전 삭제”를 위해 반드시 만든다.

1) `scripts/tests/db_crypto_assert_counts.py`
   - 역할: 특정 심볼/기간에 대해 `crypto_symbol_master`, `crypto_prices_daily`, `crypto_indicators_daily` row count를 출력
   - 입력: `--symbol BTCUSDT --start YYYY-MM-DD --end YYYY-MM-DD`
   - 출력(필수 항목):
     - prices rows, indicators rows
     - indicators distinct indicator 목록
     - min(date)/max(date)

2) `scripts/tests/db_crypto_cleanup.py`
   - 역할: 특정 심볼/기간 데이터 삭제(테스트 정리)
   - 입력: `--symbol BTCUSDT --start YYYY-MM-DD --end YYYY-MM-DD`
   - 삭제 대상:
     - `crypto_indicators_daily` (먼저)
     - `crypto_prices_daily` (다음)
   - 출력: 삭제 row 수

> 주의: `crypto_symbol_master`는 일반적으로 "마스터"이므로 테스트마다 삭제하지 않는다.
> (원하면 `--purge-symbol-master` 옵션으로 별도 삭제 가능)

---

#### (T3) 심볼 마스터 동기화 테스트

1) 실행(사용자)
```bash
python scripts/crypto_sync_symbol_master.py --all
```

2) 적재 확인(사용자): (T3에서는 기간이 없으므로 심볼 개수/샘플만)
```bash
python scripts/tests/db_crypto_assert_symbol_master.py --quote USDT --limit 10
```

3) 기대 결과
- `crypto_symbol_master`에 `BTCUSDT`, `ETHUSDT` 같은 USDT 페어가 존재
- status가 ACTIVE(TRADING 기반)로 적재

4) 정리
- (기본) 없음

---

#### (T4) 단일 심볼 Bulk 적재(가격) 테스트

목표: Binance → `crypto_prices_daily`에 insert_only로 적재되는지 확인

1) 실행(사용자)
```bash
python scripts/crypto_bulk_update_daily.py --symbols BTCUSDT --start 2026-01-01 --end 2026-01-31
```

2) 적재 확인(사용자)
```bash
python scripts/tests/db_crypto_assert_counts.py --symbol BTCUSDT --start 2026-01-01 --end 2026-01-31
```

3) 기대 결과(최소)
- prices rows > 0
- min/max date가 요청 범위 안에 존재

4) 정리(사용자)
```bash
python scripts/tests/db_crypto_cleanup.py --symbol BTCUSDT --start 2026-01-01 --end 2026-01-31
```

---

#### (T5) 단일 심볼 Bulk 적재 + 지표(SMA 5/20/40) 테스트

목표: 가격 적재 후 지표가 `crypto_indicators_daily`에 들어가는지, indicator 이름이 기대값인지 확인

1) 실행(사용자)
```bash
python scripts/crypto_bulk_update_daily.py --symbols BTCUSDT --start 2026-01-01 --end 2026-01-31 --with-indicators
```

2) 적재 확인(사용자)
```bash
python scripts/tests/db_crypto_assert_counts.py --symbol BTCUSDT --start 2026-01-01 --end 2026-01-31
```

3) 기대 결과(최소)
- indicators rows > 0
- distinct indicator에 아래가 포함
  - `sma_5_close`, `sma_20_close`, `sma_40_close`

4) 정리(사용자)
```bash
python scripts/tests/db_crypto_cleanup.py --symbol BTCUSDT --start 2026-01-01 --end 2026-01-31
```

---

#### (T6) 멱등성(insert_only) 테스트

목표: 같은 기간/같은 심볼을 2번 실행해도 row 수가 증가하지 않는지 확인

1) 1차 실행(사용자)
```bash
python scripts/crypto_bulk_update_daily.py --symbols BTCUSDT --start 2026-01-01 --end 2026-01-31 --with-indicators
python scripts/tests/db_crypto_assert_counts.py --symbol BTCUSDT --start 2026-01-01 --end 2026-01-31
```

2) 2차 실행(사용자)
```bash
python scripts/crypto_bulk_update_daily.py --symbols BTCUSDT --start 2026-01-01 --end 2026-01-31 --with-indicators
python scripts/tests/db_crypto_assert_counts.py --symbol BTCUSDT --start 2026-01-01 --end 2026-01-31
```

3) 기대 결과
- 1차/2차의 prices rows / indicators rows가 동일

4) 정리(사용자)
```bash
python scripts/tests/db_crypto_cleanup.py --symbol BTCUSDT --start 2026-01-01 --end 2026-01-31
```

---

#### (T7) daily_update(최근 기간) 테스트

목표: daily_update가 최신 구간만 가져오고, 지표 계산까지 수행되는지 확인

1) 실행(사용자)
```bash
python scripts/crypto_daily_update.py --symbols BTCUSDT --with-indicators
```

2) 적재 확인(사용자)
> daily_update는 기본적으로 end_date를 "UTC 어제"로 잡고, 최근 50일(고정) 범위를 적재합니다.

```bash
python scripts/tests/db_crypto_assert_counts.py --symbol BTCUSDT --days 50
```

3) 정리(사용자)
```bash
python scripts/tests/db_crypto_cleanup.py --symbol BTCUSDT --days 50
```

---

### 7.3. 테스트 실행 순서(추천)

1) T1, T2 (오프라인)
2) T3 (심볼 마스터)
3) T4 (가격)
4) T5 (가격+지표)
5) T6 (멱등성)
6) T7 (daily)

---

## 10) 작업 순서(권장)

Phase 1 (코인 일봉 + SMA 3종)
1. 테이블 스키마 추가 (`crypto_symbol_master`, `crypto_prices_daily`, `crypto_indicators_daily`)
2. Binance 심볼 동기화 스크립트 추가
3. Binance 일봉 collector 추가
4. Bulk 적재 스크립트 추가
5. Daily 업데이트 스크립트 추가
6. 지표 계산/저장 연결 + NULL 저장 정책 적용
7. 테스트/검증(단위→통합→멱등)
8. 문서(적재작업_가이드.md와 유사한 crypto 가이드) 추가

---

## 12) 테스트 스크립트 목록(작성 위치 고정)

모든 테스트/검증/정리 스크립트는 아래 디렉토리에 생성한다.
- `scripts/tests/`

### 오프라인 단위 테스트
- `scripts/tests/test_crypto_binance_exchangeinfo_parse.py`
- `scripts/tests/test_crypto_binance_klines_parse.py`

### DB 확인/삭제 도구(반드시 분리)
- `scripts/tests/db_crypto_assert_symbol_master.py`
- `scripts/tests/db_crypto_assert_counts.py`
- `scripts/tests/db_crypto_cleanup.py`

### 통합 테스트(원하면 추가)
- `scripts/tests/test_crypto_bulk_one_symbol_smoke.py` (실제 bulk 실행을 래핑하는 스모크; 선택)

> 본 계획서는 Copilot이 터미널 실행을 대신하지 않는 것을 전제로 한다.
> 따라서 각 테스트의 실행 커맨드와 기대 출력/정리 절차를 명시적으로 고정했다.
