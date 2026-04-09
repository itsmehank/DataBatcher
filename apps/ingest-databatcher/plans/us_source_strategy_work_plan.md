# US Source Strategy Work Plan

## 목적

`daily_us.sh`의 US-1, US-2 단계에서 사용하는 가격 소스를
설정/CLI 기반 `source_strategy`로 선택 가능하게 만들기 위한 작업 계획이다.

중요:

- 이 문서는 **구현 승인 전 검토용 계획서**다.
- 본 계획서는 `apps/ingest-databatcher/plans/us_yfinance_preflight_report.md`의 결과를 전제로 한다.
- 이 단계에서는 실제 구현을 수행하지 않는다.

---

## 1. 목표 범위

대상:

- `apps/ingest-databatcher/scripts/us_daily_update.py`
- `apps/ingest-databatcher/scripts/us_index_daily_update.py`
- `apps/ingest-databatcher/collectors/us_stock.py`
- `apps/ingest-databatcher/collectors/us_index.py`
- 관련 설정/문서/프로브

이번 변경의 목표:

1. US 주식/지수 daily 수집에서 provider strategy를 명시적으로 선택 가능하게 만들기
2. FDR, yfinance, fallback 전략을 공통 collector 구조 안에서 지원하기
3. downstream(RS/Minervini)은 DB-only 구조를 유지하기
4. 실제 사용 provider provenance를 DB row에 남기기

이번 변경에서 하지 않을 것:

1. RS / Minervini 계산 로직 자체 변경
2. `us_symbol_master` 구조 대개편
3. bulk / weekly까지 한 번에 확장
4. hidden automatic fallback 도입

---

## 2. 권장 설계

### 2-1. 전략 이름

초기 지원 전략:

- `fdr`
- `yfinance`
- `fdr_then_yfinance`

원칙:

- 기본값은 `fdr`
- fallback은 기본 동작이 아니라 **전략 이름으로 명시**한다

### 2-2. 설정 우선순위

권장 우선순위:

1. CLI 옵션
2. `settings.dev.yaml`
3. `settings.yaml`
4. 코드 기본값

예시 설정 구조:

```yaml
collectors:
  us_stock:
    source_strategy: fdr
  us_index:
    source_strategy: fdr
```

예시 CLI:

```bash
python apps/ingest-databatcher/scripts/us_daily_update.py --all --with-indicators --source-strategy yfinance
python apps/ingest-databatcher/scripts/us_index_daily_update.py --all --source-strategy fdr_then_yfinance
```

### 2-3. collector 구조

권장 구조:

- 상위 collector는 유지
  - `USStockCollector`
  - `USIndexCollector`
- 내부에 provider별 fetch 메서드 추가
  - `_fetch_via_fdr(...)`
  - `_fetch_via_yfinance(...)`
- `fetch(...)`는 strategy dispatcher 역할만 수행

이유:

- 현재 daily 파이프라인의 공통 로직을 유지할 수 있음
- provider별 차이만 collector 내부에 가둘 수 있음
- KR index의 `source_strategy` 패턴과 유사하게 가져갈 수 있음

---

## 3. 구현 전 게이트

아래 게이트를 통과해야 구현을 시작한다.

### Gate A. 사전 적합성 확인

근거 문서:

- `apps/ingest-databatcher/plans/us_yfinance_preflight_report.md`

통과 조건:

- 주식/지수 모두 입력 인자 정의 완료
- 지수 symbol resolver 초안 확정
- `yfinance` MultiIndex 정규화 방안 확정
- `auto_adjust=False` 유지 원칙 확정

### Gate B. 추가 샘플 검증

구현 전 보완 검증:

1. 특수 심볼 샘플 5~10개
2. ETF 샘플 3개 이상
3. index 3종 전 기간 샘플 비교
4. `Adj Close` / `Volume` 결측 여부 점검

통과 조건:

- collector 정규화에 필요한 예외 케이스 목록 작성 완료

### Gate C. 변경 설계 검토

확정해야 할 항목:

1. `settings.yaml` 키 구조
2. CLI 옵션 이름
3. row-level `source` 저장 규칙
4. 실패 시 로그 메시지 형식
5. fallback strategy에서 어떤 provider가 실제 사용되었는지 노출하는 방식

---

## 4. 실제 구현 순서

구현 승인이 나면 아래 순서로 진행한다.

### Phase 1. Probe/Test 보강

목표:

- 구현 전에 재현 가능한 검증 경로 확보

작업:

1. `apps/ingest-databatcher/scripts/probes/` 아래에 yfinance 전용 US stock/index probe 추가 또는 기존 probe 확장
2. 대표 샘플군 비교 실행 결과 문서화
3. 필요하면 comparison report 템플릿 추가

산출물:

- probe 스크립트
- 비교 결과 문서

### Phase 2. US Stock collector 전략화

목표:

- `USStockCollector`에 `source_strategy` 도입

작업:

1. `__init__(..., source_strategy="fdr")` 추가
2. `_fetch_via_fdr(...)` 분리
3. `_fetch_via_yfinance(...)` 추가
4. MultiIndex flatten / 날짜 / 컬럼명 / source 정규화
5. fallback 전략 dispatcher 추가

성공 기준:

- `us_daily_update.py` 기존 흐름 수정 없이 collector만 교체 가능

### Phase 3. US Index collector 전략화

목표:

- `USIndexCollector`에 `source_strategy`와 symbol resolver 도입

작업:

1. 내부 심볼 -> provider 심볼 매핑 추가
2. `_fetch_via_fdr(...)` 분리
3. `_fetch_via_yfinance(...)` 추가
4. index 전용 정규화 규칙 반영

성공 기준:

- `US500`, `DJI`, `IXIC`를 공통 내부 심볼로 유지하면서 provider 교체 가능

### Phase 4. Script wiring

목표:

- daily 스크립트가 config/CLI에서 전략을 읽어 collector에 주입

작업:

1. `us_daily_update.py` CLI 옵션 추가
2. `us_index_daily_update.py` CLI 옵션 추가
3. 설정 fallback 로직 추가
4. 로그에 선택 전략 출력

### Phase 5. Verification

목표:

- 전략별로 동일 파이프라인이 정상 동작하는지 검증

검증 축:

1. `fdr`
2. `yfinance`
3. `fdr_then_yfinance`

검증 항목:

1. collector 출력 컬럼 일치
2. DB insert_only 적재 성공
3. `source` 컬럼 정확성
4. downstream RS/Minervini 재사용 가능성
5. 문서 업데이트

---

## 5. 설계 원칙

1. 공통 파이프라인은 유지하고 provider 차이만 adapter 계층에서 흡수한다.
2. fallback은 숨기지 않고 strategy 이름으로 명시한다.
3. 실제 사용 provider는 row-level `source`에 남긴다.
4. `Close`와 `Adj Close`는 절대 혼합하지 않는다.
5. index symbol 매핑은 collector 내부 resolver 책임으로 둔다.
6. downstream 단계는 DB-only 구조를 유지한다.

---

## 6. 주요 리스크와 대응

### 리스크 1. yfinance MultiIndex 컬럼

대응:

- provider adapter 내부에서 1차원 컬럼으로 flatten

### 리스크 2. 날짜 경계 차이

대응:

- provider별 `end` 처리 방식을 collector 내부에서 명시적으로 캡슐화

### 리스크 3. index ticker 매핑 누락

대응:

- 고정 매핑 테이블 추가
- unsupported symbol은 즉시 명시적 에러

### 리스크 4. provider 혼합 데이터 해석 어려움

대응:

- `source` 컬럼 정확히 유지
- fallback 전략 사용 시 로그에 실제 provider 노출

### 리스크 5. downstream 지표 일관성

대응:

- `Adj Close` 기반 설정(`ibd_rs.us_price_column`, `minervini_us.price_column`)과의 정합성 확인

---

## 7. 구현 승인 전 최종 확인 질문

구현 시작 전에 아래를 사용자와 최종 합의하는 것이 좋다.

1. 기본 전략을 계속 `fdr`로 둘지
2. `fdr_then_yfinance`를 초기 버전에 포함할지
3. bulk / weekly까지 동시에 확장할지, daily만 먼저 할지
4. probe/test 보강을 어디까지 하고 구현에 들어갈지

---

## 8. 현재 제안

현재 가장 안전한 진행 순서는 아래와 같다.

1. 이 계획서 검토
2. 승인 시, probe/test 보강부터 수행
3. 그 결과를 반영해 collector 전략화 구현
4. daily US만 먼저 반영
5. 검증 후 bulk/weekly 확장 여부 판단

즉, **바로 구현하지 않고 `preflight -> 설계 확정 -> 구현` 순서로 가는 것이 맞다.**
