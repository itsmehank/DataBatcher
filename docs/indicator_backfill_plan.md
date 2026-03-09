# 추가 지표 백필(Backfill) 기능 구현 계획서 (v5)

> 목적: **이미 적재된 원본 테이블(일봉/주봉)을 대상으로, 신규 지표를 계산해 지표 테이블에 추가 적재**하는 독립 실행 도구를 만든다.
> 
> 핵심 요구사항
> - **추가 지표 전용 설정 파일(YAML)** 로 지표 목록을 받는다.
> - YAML 포맷은 **기존 `IndicatorPipeline` 스펙과 호환**된다.
> - 실행은 **항상 전체 기간(full history)** 을 대상으로 한다. (사용자 입력으로 start/end를 받지 않는다)
> - 적재 시 **이미 (symbol, date(or week_start), indicator, params_hash) 가 존재하면 건너뛴다**(update 금지).

---

## 0. 현재 코드베이스 기준(근거)

이 계획은 현재 레포의 다음 컴포넌트를 그대로 재사용한다.

- 지표 실행 파이프라인: `indicators/pipeline.py`
  - `IndicatorPipeline(specs)`
  - `to_long_dataframe()`가 long-form(`symbol,date,indicator,params_hash,value,market,source`)을 만든다.
  - **주의:** 현재 구현은 `dropna(subset=["value"])`로 NaN을 저장하지 않는다.
- 지표 저장: `savers/indicator_saver.py`
  - `IndicatorSaver.save_long(df_long, mode="insert_only")`
  - 내부에서 `DBManager.upsert_dataframe(..., mode="insert_only")` 호출
  - 유니크 키: `(symbol, date, indicator, params_hash)`

왜 재사용하나?
- 이미 프로젝트에서 검증된 저장 방식/키 설계를 그대로 쓰면, 신규 기능이 기존 시스템과 일관되게 동작한다.
- 특히 **insert-only(기존값 보존)** 정책을 안전하게 구현할 수 있다.

---

## 1. 기능 정의(Contract)

### 1.1 입력(Inputs)

#### CLI 입력
- `--timeframe {daily,weekly}` (필수)
  - daily: 일봉 원본 → 일봉 지표
  - weekly: 주봉 원본 → 주봉 지표
- `--indicators-config <path>` (필수)
  - **추가 지표 전용 YAML**
  - 기존 `IndicatorSpec` 포맷과 호환
- 심볼 범위 선택(**둘 중 하나는 필수**)
  - `--symbols 005930 000660 ...`
  - `--all`
  - 둘 다 없으면 실행 전에 에러로 종료한다.
- `--market {KOSPI,KOSDAQ,KONEX,ALL}` (선택, 기본 ALL)
  - `--all`일 때만 유효(특정 시장의 심볼만 처리)
  - **중요:** `--market`은 *대상 심볼 필터링*에만 사용한다.
- (선택) `--top N`
  - `--all`일 때 시총 상위 N개만
- (선택) `--dry-run`
  - 저장 없이 예측/요약 정보만 출력
- (선택) `--log-failures <path>`

#### 실행 데이터 규칙(스키마/운영 정책 확정)

##### market/source 저장 규칙(확정)
- backfill(추가 지표 생성) 시, 지표 테이블의 `market`, `source`는 **원본 소스 테이블(row)에서 읽은 값을 그대로 사용**한다.
  - daily: `stock_prices.market`, `stock_prices.source`
  - weekly: `stock_prices_weekly.market`, `stock_prices_weekly.source`
- 즉, `--market` 같은 필터 값으로 `market` 컬럼을 덮어쓰지 않는다.

> 근거/이유
> - `--market`은 이 레포에서 “대상 심볼을 고르는 용도”로 사용된다.
> - 저장값까지 덮어쓰기 시작하면, 원본 테이블과 지표 테이블의 `market/source` 데이터 계보(lineage)가 끊긴다.

##### symbol 처리(정규화) 정책
- DB 스키마 상 `symbol`은 `VARCHAR(32)`이며, 본 기능은 **symbol을 끝까지 문자열로 처리**한다.
- 원본 테이블에 저장된 `symbol` 값을 그대로 사용한다.
- (안전장치) CLI로 `--symbols`를 입력받는 경우에는, 사용자 실수를 줄이기 위해 아래를 권장한다.
  - 숫자만 들어온 경우(예: `2222`)를 `zfill(6)`로 보정할지 여부는 추후 옵션으로 둔다.
  - 단, 이 보정은 “원본 DB에 이미 6자리로 저장되어 있다”는 전제에서만 의미가 있다.

##### 결측치/비정상 값 처리(확정)
- 원본 가격 데이터에서 **OHLC 중 하나라도 NULL 또는 0이면 해당 row는 지표 계산 입력에서 제외**한다.
- `volume`은 0/NULL이어도 **입력에서 제외하지 않는다(허용)**.

> 근거/이유
> - OHLC는 대부분의 가격 기반 지표의 핵심 입력이며, 0/NULL은 비정상 데이터로 보는 것이 일반적이다.
> - volume=0은 “거래량 없음”으로 해석 가능한 경우가 있어, 일괄 제외하면 의도치 않은 누락이 발생할 수 있다.

#### 설정(YAML) 입력
- `indicators.pipeline` 하위에 추가할 지표만 나열

> 왜 지표 목록을 YAML로 받나?
> - CLI로 지표/파라미터를 모두 나열하면 재현성이 낮고, 추후 재실행/추적이 어렵다.
> - YAML을 실행 기록으로 남기면 “언제 어떤 지표를 어떤 파라미터로 추가했는지”가 명확해진다.

#### 실행 전 사전 검증(필수)
`scripts/backfill_indicators.py` 시작 시점에 아래를 검증하고, 실패하면 **처리 시작 전에 즉시 종료**한다.

1) YAML 파싱 가능 여부
2) `indicators.pipeline` 존재 및 리스트 형식 여부
3) 각 spec이 `name`, `params`를 포함하는지
4) `IndicatorRegistry`에 `name`이 등록되어 있는지

> 왜 사전 검증이 중요한가?
> - 수백/수천 종목을 처리하기 시작한 뒤에 “지표 미등록” 같은 설정 오류가 터지면 운영 비용이 매우 커진다.
> - 초기에 실패하게 만들면 장애 원인 파악과 재실행이 쉽다.

### 1.2 출력(Outputs)
- 지정된 timeframe의 **지표 테이블**에 long-form row가 INSERT(존재하면 SKIP)
- 실행 요약 리포트(콘솔): 처리 심볼 수, insert row 수, 실패 심볼
- 실패 로그 파일(옵션)

### 1.3 비목표(Non-goals)
- 가격 데이터 수집/적재는 하지 않는다.
- 기존 지표 업데이트(UPSERT)는 하지 않는다.
- 사용자 입력으로 기간(start/end)을 지정하지 않는다.

---

## 2. “전체 기간”인데 start/end 체크가 필요 없는가?

### 결론: **사용자 입력으로 start/end를 받는 기능은 필요 없다(요구사항대로 제거)**.

다만, 구현 내부에서는 아래 이유로 “기간 개념”이 **암묵적으로는 필요**하다.

- 원본 테이블에서 데이터를 읽으려면, 결국 DB 쿼리를 위해
  - `MIN(date)` / `MAX(date)` 같은 범위를 구하거나
  - 전체를 조회해야 한다.
- 지표 계산에는 warmup이 필요할 수 있어, **계산용 조회 범위**는 `min_date - warmup`로 확장될 수 있다.

따라서 이 기능은:
- CLI에 `--start/--end` 옵션은 없다.
- 내부에서는 테이블에서 `min/max`를 조회하거나, 전체를 가져오되
  - 성능을 위해 심볼 단위로 분리해서 처리한다.

---

## 3. 테이블/컬럼 매핑(Timeframe Mapping)

`--timeframe`에 따라 기본 매핑을 제공한다.

| timeframe | source_table | target_table | date_column |
|---|---|---|---|
| daily | `stock_prices` | `stock_indicators` | `date` |
| weekly | `stock_prices_weekly` | `stock_indicators_weekly` | `week_start` |

> 왜 timeframe을 받나?
> - 이 레포는 일봉/주봉이 **테이블명과 날짜 컬럼명이 다르다**.
> - 사용자에게 테이블/컬럼을 매번 직접 받게 하면 실수가 늘고 UX가 나빠진다.
> - 내부적으로는 이 매핑을 통해 “같은 backfill 로직”을 재사용한다.

---

## 4. YAML 포맷(기존 pipeline spec 호환)

파일 예시: `config/backfill_indicators.sample.yaml`

```yaml
indicators:
  pipeline:
    - name: rsi
      params:
        window: 14
        column: close
      save: true

    - name: sma
      params:
        window: 50
        column: close
      save: true
```

규칙:
- `indicators.pipeline`는 기존 `config/settings.yaml`과 동일한 구조를 사용한다.
- **여기에는 “이번에 추가할 지표”만 넣는다.**
  - 기존 배치(daily/weekly)가 계산하는 지표 목록과 분리됨.

---

## 5. 처리 흐름(Algorithm)

### 5.1 심볼 목록 결정
1) `--symbols`가 있으면 해당 목록
2) `--all`이면 `core/symbol_loader.py`의 `load_symbols_from_master()`를 재사용
   - `market`, `top` 필터 적용

> 왜 symbol_master 기반인가?
> - 기존 daily/weekly 스크립트도 같은 방식으로 대상 심볼을 결정한다.
> - “운영에서 ACTIVE 심볼만 대상으로 한다”는 프로젝트 규칙을 재사용할 수 있다.

### 5.2 심볼 단위로 전체 기간 로드
- 각 심볼에 대해 원본 테이블에서 해당 심볼의 전체 기간 데이터를 조회
- 조회는 date_column 기준 정렬
- warmup은 `pipeline.warmup_days()`만큼 고려

성능/안정성 이유:
- 전체 종목을 한 번에 로드하면 메모리 폭발 가능
- 심볼 단위로 처리하면 실패 격리/재시도가 쉬움

### 5.3 지표 계산
- DataFrame의 인덱스를 datetime으로 맞춘 뒤 `pipeline.run(df)` 실행
- 결과(outputs)를 `pipeline.to_long_dataframe(...)`로 long-form으로 변환
- `timeframe=weekly`인 경우:
  - `to_long_dataframe`는 컬럼명을 `date`로 생성하므로, 저장 전에 **반드시** `week_start`로 rename

권장 구현 형태(의사코드):
- `df_long = pipeline.to_long_dataframe(...)`
- `if timeframe == "weekly": df_long = df_long.rename(columns={"date": "week_start"})`

> 왜 weekly rename을 명시적으로 강제하나?
> - 이 레포에서 주봉 지표 테이블은 날짜 컬럼이 `week_start`이며, 일봉(`date`)과 다르다.
> - 이 처리가 누락되면 주봉 저장 시 컬럼 불일치/DB 에러가 발생한다.

### 5.4 저장(INSERT ONLY)
- `IndicatorSaver(table_long=target_table).save_long(df_long, mode="insert_only")`
- 이미 존재하는 row는 DB에서 ignore되어 수정되지 않는다.

#### params_hash 및 “동일 지표 재실행” 동작 정의(명확화)
- 이 프로젝트의 long-form 지표 테이블 유니크 키는 `(symbol, date(or week_start), indicator, params_hash)`다.
- 따라서 **동일한 (indicator, params) → 동일 params_hash**로 backfill을 다시 실행하면:
  - insert-only 이므로 새 row는 추가되지 않고
  - 기존 row는 보존된다

이는 요구사항(기존 데이터 유지, update 금지)에 부합하는 의도된 동작이다.

---

## 6. 모듈/파일 설계

### 6.1 신규 파일
1) `core/indicator_backfiller.py`
- 백필 핵심 로직(재사용 가능)
- 책임:
  - 심볼 목록 처리
  - 원본 데이터 로드
  - pipeline 실행
  - long-form 변환
  - insert-only 저장
  - 결과 요약/실패 로깅

2) `scripts/backfill_indicators.py`
- CLI 진입점
- 책임:
  - argparse
  - 설정 로드(`load_settings()` + indicators-config 로드)
  - Engine 생성
  - Backfiller 호출

3) `config/backfill_indicators.sample.yaml`
- 샘플 설정

### 6.2 기존 파일 수정(최소화)
- 원칙: 기존 daily/weekly/bulk 스크립트에는 영향 최소
- 이번 기능 구현에 기존 코드를 직접 수정해야 할 가능성은 낮다.

---

## 6.3 신규 지표(Indicator) 플러그인 추가/제거 전략 (중요)

이 프로젝트는 `IndicatorRegistry`(레지스트리 패턴) 기반이며, **신규 지표 클래스를 추가한 뒤 레지스트리에 등록되도록 “import가 실행”되어야** 한다.

- 등록 방식: `@IndicatorRegistry.register` 데코레이터
- 주의점: 파일을 만들어도 import가 한 번도 발생하지 않으면 Registry에 등록되지 않는다.

### 6.3.1 신규 지표 추가 절차(개발)
1) `indicators/common/` 아래에 신규 파일 추가
   - 예: `indicators/common/rsi.py`
2) `BaseIndicator`를 상속하고 필수 메서드 구현
   - `required_columns()`, `warmup()`, `compute()`
3) 클래스에 `@IndicatorRegistry.register`를 적용
4) (필요 시) `compute()` 결과 Series의 `name`을 유니크하게 지정
   - 예: `rsi_{window}_{column}`

> 왜 Series.name이 중요한가?
> - 현재 `IndicatorPipeline.to_long_dataframe()`는 결과 key/series.name을 `indicator` 컬럼 값으로 저장한다.
> - 파라미터가 다른 동일 지표가 공존하려면 name이 충돌하지 않도록 구성해야 한다.

### 6.3.2 추가 지표 “켜고/끄기” (운영)
- backfill에서 특정 지표를 추가하고 싶으면 `--indicators-config` YAML에 해당 spec을 추가
- 더 이상 사용하지 않으면 YAML에서 제거거나 `save: false`로 비활성화

> 참고: insert-only 정책이므로, YAML에서 제거해도 DB에 이미 적재된 과거 지표 row는 자동 삭제되지 않는다.

---

## 6.4 레지스트리 자동 등록(import) 구조 개선 계획 (기존 작업과 호환)

### 목표
- 신규 지표 파일을 `indicators/common/`에 추가하면,
  - backfill 스크립트뿐 아니라
  - 기존 작업(일봉 daily/bulk, 주봉 weekly/bulk_weekly)의 지표 생성에서도
  **추가 import 수정 없이 자동으로 레지스트리에 등록되게 만든다.**

### 현재 문제(현 코드 근거)
- `scripts/daily_update.py`, `scripts/bulk_update.py` 등은 레지스트리 등록을 위해 특정 지표 모듈을 직접 import한다.
  - 예: `from indicators.common import sma as _reg_sma` / `ema as _reg_ema`
- 신규 지표를 추가할 때마다 여러 스크립트의 import 라인을 늘려야 하는 구조가 될 수 있다.

### 개선 방향(권장)
1) `indicators/common/__init__.py`를 “등록용 aggregator(집합 import)”로 적극 활용한다.
   - `__init__.py`에서 common 지표 모듈들을 import하여, `import indicators.common` 한 번으로 등록이 완료되게 한다.

2) 각 실행 스크립트는 개별 지표 import 대신 아래 1줄만 유지한다.
   - `import indicators.common  # noqa: F401`

3) 신규 지표 추가 시에는:
   - `indicators/common/rsi.py` 파일 추가
   - `indicators/common/__init__.py`에 `from . import rsi  # noqa: F401` 한 줄 추가
   - (이렇게 하면 daily/weekly/bulk/backfill 모두 별도 변경 없이 사용 가능)

> 왜 __init__.py에 명시 import를 두나?
> - “폴더 내 파일을 자동 탐색해서 import”는 구현 가능하지만(동적 import),
>   예측 가능성과 디버깅 관점에서 명시 import가 운영에 더 안전하다.

### 적용 대상 파일(계획)
- (신규) `indicators/common/__init__.py`에 공통 지표 import 목록 정리
- (수정) `scripts/daily_update.py`, `scripts/bulk_update.py`
  - 개별 지표 import를 제거하고 `import indicators.common`으로 교체
- (수정) 주봉 스크립트들에도 동일 적용
  - `scripts/weekly_update.py`, `scripts/bulk_update_weekly.py` 등
- (수정) 이번에 만들 backfill 스크립트도 동일 규칙 적용

---

## 7. 예외/엣지 케이스

- 원본 데이터가 없는 심볼
  - skip 처리 + 로그
- 특정 지표 클래스 미등록(IndicatorRegistry에 없음)
  - 즉시 실패(사용자 설정 오류)
- warmup 부족으로 값이 NaN인 초반 구간
  - 현재 파이프라인이 dropna로 제거 → DB row가 생성되지 않음
  - 즉, 예: SMA(20)이라면 초반 19개 구간은 해당 지표 row가 존재하지 않을 수 있음
  - 이 동작은 현재 코드베이스(`IndicatorPipeline.to_long_dataframe`)의 정책이다.
  - (추후 개선) NaN도 NULL로 저장하는 정책은 스키마/성능 영향이 커서 별도 과제로 둔다.
- 주봉 집계 규칙(거래일/캘린더) 확정
  - `week_start`~`week_end`(월~금) 범위 내에서
    - `open`: 가장 빠른 개장일의 open
    - `close`: 가장 늦은 개장일의 close
    - `high`: 기간 내 high의 max
    - `low`: 기간 내 low의 min
    - `volume`: 기간 내 volume의 sum
  - 월~금 전체 휴장(거래일 0일)이면 해당 주차 데이터는 생성/삽입하지 않는다.

---

## 8. 테스트/검증 계획 (바로 구현 가능한 수준)

### 8.1 최소 수동 검증(개발자가 로컬에서)
- 1~2개 심볼로 dry-run
- 실제 실행 후 insert row 수 확인
- 동일 실행 2회 수행 → 2회차 insert row가 0에 가까운지(완전 동일이면 0) 확인

### 8.2 자동 테스트(구체)

이 레포의 테스트는 `pytest`만을 전제하지 않고, `tests/test_phase*.py`처럼 **단독 실행 가능한 파이썬 스크립트** 형태를 사용한다.
또한 테스트 DB 격리를 위해 `DATABASE_URL`을 `trade_test`로 설정하고, 서브프로세스로 실행되는 스크립트들도 동일 DB를 사용한다.

근거:
- `tests/README_TEST_DB.md`: 테스트 DB는 `trade_test`, `DATABASE_URL`로 주입, 종료 후 row delete 방식
- `tests/test_phase2_bulk_update.py`: `os.environ["DATABASE_URL"] = get_test_db_url()` 후 `subprocess.run([...], env=env)`

#### 8.2.0 사전 조건(One-time)
1) 테스트 DB 생성/스키마 적용

```bash
python tests/test_db_setup.py --create
```

2) 테스트 실행 시, 스크립트들은 자동으로 `DATABASE_URL`을 설정하지만,
   개발자가 수동 실행할 경우에도 동일 방식으로 `DATABASE_URL`을 유지해야 한다.

---

### 8.2.1 테스트 파일 구성(신규 추가)

아래 테스트를 신규로 추가한다.

1) `tests/test_phase5_backfill_indicators_daily.py`
- 목적: **일봉 backfill**이 동작하고, insert-only 멱등성이 성립하는지 검증

2) `tests/test_phase6_backfill_indicators_weekly.py`
- 목적: **주봉 backfill**이 동작하고, `week_start` 컬럼 매핑 및 멱등성이 성립하는지 검증

3) (선택) `tests/test_phase5_1_backfill_indicators_validation.py`
- 목적: YAML 사전 검증이 제대로 실패하는지(지표 미등록/스펙 오류) 검증

> 왜 Phase 테스트로 추가하나?
> - 기존 테스트 문화와 동일한 형태로 유지하면 러너(`tests/run_all_tests.py`)에 쉽게 편입할 수 있다.
> - DB를 포함한 통합 테스트에서 `subprocess`로 실제 스크립트를 실행하는 패턴이 이미 자리 잡혀 있다.

---

### 8.2.2 공통 테스트 유틸(테스트 코드에서 재사용)

각 test_phase 파일에 공통으로 들어갈 유틸(또는 `tests/_utils.py`로 분리 가능):

- `test_db_url = get_test_db_url()` 확보 후 `os.environ["DATABASE_URL"] = test_db_url`
- `env = os.environ.copy(); env["PYTHONPATH"] = str(ROOT)`
- `subprocess.run([sys.executable, <script-path>, ...], env=env, capture_output=True, text=True)`

또한 테스트 종료 시 **테이블 row cleanup**을 수행한다.
(기존 테스트들은 각 phase마다 cleanup을 직접 정의하거나 `run_all_tests.py`에서 일괄 cleanup을 수행)

---

### 8.2.3 Phase 5: 일봉 backfill 통합 테스트 시나리오(상세)

파일: `tests/test_phase5_backfill_indicators_daily.py`

#### 테스트 목적
- backfill 스크립트가 **가격 수집/적재 없이** `stock_prices`를 읽어 지표를 적재하는지
- 지표 적재가 **insert-only**로 수행되어, 2회 실행 시 row 수가 증가하지 않는지(멱등성)

#### 준비 데이터
- 테스트 DB에 `stock_prices`가 채워져 있어야 한다.
  - 가장 현실적인 방법: 기존 Phase 1/2 테스트를 선행하거나, 테스트 내부에서 `bulk_update.py`를 아주 짧은 기간으로 실행한다.

권장 방식(테스트 내부에서 자급자족):
1) (필요 시) `tests/test_phase1_sync_symbol_master.py`를 먼저 실행
2) `scripts/bulk_update.py --top 3 --start <today-30d> --end <today>` 실행

> 왜 bulk_update를 호출하나?
> - backfill은 “원본 테이블 기반”이므로, 원본 데이터가 없는 상태에서 의미 있는 검증이 어렵다.
> - 레포에 이미 있는 수집 스크립트를 활용하면 실제 실행 경로를 그대로 테스트할 수 있다.

#### 테스트 단계
1) Setup
- `DATABASE_URL`을 test DB로 설정
- 테스트용 YAML 파일을 임시 생성(또는 `config/backfill_indicators.sample.yaml` 이용)
  - 단, 샘플이 rsi를 포함할 경우, 레지스트리에 rsi가 없으면 실패하므로 테스트에서는 **sma/ema 등 이미 존재하는 지표**를 우선 사용한다.

2) Pre-check: backfill 전 지표 row count 확인
- `SELECT COUNT(*) FROM stock_indicators WHERE symbol in (...) AND indicator LIKE 'sma_%'` 등으로 baseline 확보

3) 1차 실행
- `scripts/backfill_indicators.py --timeframe daily --symbols <3개> --indicators-config <yaml>` 실행
- returncode == 0 확인

4) 1차 실행 후 검증
- `stock_indicators`에 row가 **0보다 큰 값으로 증가**했는지 확인
- (필수) 최소 컬럼 검증
  - `indicator`, `params_hash`, `value`가 NULL이 아닌 row 존재

5) 2차 실행(멱등성 검증)
- 동일 명령으로 backfill을 한 번 더 실행

6) 2차 실행 후 검증
- 1차 후 row count == 2차 후 row count 여야 한다(또는 증가량이 0)
- 이는 insert-only + 동일 params_hash 동작이 유지됨을 의미

7) Cleanup
- `DELETE FROM stock_indicators`, `DELETE FROM stock_prices`, `DELETE FROM symbol_master` (테스트 DB에 한정)

#### 실패 시 디버깅 출력(테스트 코드에 포함)
- backfill 스크립트 stdout/stderr를 그대로 출력
- row count, 심볼 목록, 사용한 YAML 내용을 출력

---

### 8.2.4 Phase 6: 주봉 backfill 통합 테스트 시나리오(상세)

파일: `tests/test_phase6_backfill_indicators_weekly.py`

#### 테스트 목적
- 주봉 backfill이 `stock_prices_weekly`를 읽어 `stock_indicators_weekly`에 insert-only로 적재하는지
- **컬럼 매핑**이 올바른지: `week_start` 컬럼으로 저장되는지
- 2회 실행해도 row 증가가 없는지(멱등성)

#### 준비 데이터
주봉 원본이 채워져 있어야 함.

현 레포 기준 선택지:
- `scripts/bulk_update_weekly.py` 또는 `scripts/weekly_update.py`를 활용해 `stock_prices_weekly`를 채운다.

테스트 내부 권장 흐름:
1) symbol_master가 준비되어 있지 않으면 Phase1 실행
2) `scripts/bulk_update_weekly.py`를 짧은 기간/소수 종목으로 실행(가능한 옵션 범위에서)

#### 테스트 단계(핵심 검증)
- backfill 1회 실행 후:
  - `SELECT COUNT(*) FROM stock_indicators_weekly WHERE symbol in (...)` > 0
  - `SELECT COUNT(*) FROM stock_indicators_weekly WHERE week_start IS NULL` == 0
- backfill 2회 실행 후:
  - row count 증가량 == 0

주의:
- weekly 스크립트들은 내부 구현이 daily와 다를 수 있으므로, 이 테스트는 “week_start rename 누락” 같은 회귀를 잡는 데 특히 유효하다.

---

### 8.2.5 Phase 5.1: YAML 사전 검증 실패 테스트(선택이지만 강력 추천)

파일: `tests/test_phase5_1_backfill_indicators_validation.py`

#### 목적
- 설정 오류를 “처리 시작 전에” 잡는지 검증

#### 케이스
1) `indicators.pipeline` 누락 YAML
2) spec에 `name` 누락
3) Registry에 없는 지표 이름(`name: __not_registered__`)

#### 검증
- backfill 스크립트 실행 returncode != 0
- stderr/stdout에 유의미한 에러 메시지 포함

---

### 8.2.6 run_all_tests.py 편입(선택)

`tests/run_all_tests.py`의 tests 목록에 Phase 5/6을 추가할 수 있다.
다만 weekly까지 포함하면 실행 시간이 늘어날 수 있으므로,
- Phase 5(daily backfill)만 기본 러너에 포함
- Phase 6(weekly backfill)은 옵션(또는 별도 실행)

같은 운영 전략도 가능하다.

---

## 9. 구현 단계(체크리스트)

### Phase 1: MVP(필수)
- [ ] `docs/indicator_backfill_plan.md` 확정(현재 문서)
- [ ] `config/backfill_indicators.sample.yaml` 추가
- [ ] `core/indicator_backfiller.py` 구현
- [ ] `scripts/backfill_indicators.py` 구현
- [ ] **YAML 사전 검증 구현**(지표 등록 여부 포함)
- [ ] **실패 복구/안전 종료 기본 동작 구현**
  - 실패한 심볼은 로그에 기록하고 다음 심볼 계속 진행
  - Ctrl+C(KeyboardInterrupt) 시 현재 심볼 처리 단위를 정리하고 요약 출력 후 종료
  - 트랜잭션 단위: 기본은 **심볼 단위 커밋**(한 심볼 실패가 전체 실행을 망치지 않도록)
- [ ] 로컬 dry-run 및 실 실행 검증
- [ ] dry-run 출력 강화(아래 섹션 참고)
- [ ] **레지스트리 자동 등록 규칙 적용**
  - `indicators/common/__init__.py`에 import aggregator 구성
  - daily/bulk/weekly/bulk_weekly/backfill 스크립트에서 `import indicators.common` 1줄로 등록되게 정리

### Phase 2: 운영 편의/성능(선택)
- [ ] 실패 심볼만 재시도 옵션(`--retry-from-log`)
- [ ] 처리 진행률/ETA 출력(tqdm)
- [ ] 성능 최적화(대량 insert chunk sizing 등)
- [ ] **병렬 처리 옵션**: `--workers N` (멀티프로세싱/스레딩)
- [ ] **사전 필터링 최적화**: 이미 모든 추가 지표가 충분히 채워진 심볼은 skip
- [ ] **메모리 최적화(청킹)**: 기간이 매우 긴 심볼(예: 5년+)은 연/월 단위 chunk 처리(warmup 오버랩 포함)

---

## 10. 성공 기준(Acceptance Criteria)

- AC1: `scripts/backfill_indicators.py`가 **가격 수집/적재 없이** 기존 원본 테이블을 읽어 신규 지표를 생성한다.
- AC2: 지표 목록은 **추가 지표 전용 YAML**로 입력받고, 기존 파이프라인 스펙(`IndicatorSpec`)과 호환된다.
- AC3: 저장은 **insert-only**이며, 기존 지표 row는 절대 변경되지 않는다.
- AC4: `--symbols` 또는 `--all`(+ `--market`)로 대상 범위를 제어할 수 있다. (둘 다 없으면 실행 전에 실패한다)
- AC5: 동일 입력으로 2회 실행 시, 두 번째 실행은 추가 insert가 발생하지 않거나(0) 매우 제한적으로만 발생한다(멱등).

---

## 11. 추후 논의할 옵션(범위 밖)

- NaN/None 값을 테이블에 저장(정상 warmup 누락 vs 오류 누락 구분)
  - 필요 시 schema 변경 + 완료 체크 로직 재설계가 필요
- 기존 지표 덮어쓰기(UPSERT) 모드
  - 현재 요구사항은 update 금지이므로 제외

## 12. dry-run 출력(권장 사양)

`--dry-run`은 단순히 “예상 row 수”만 보여주는 것을 넘어서, 운영자가 실행 범위를 빠르게 검증할 수 있는 정보를 출력한다.

권장 출력 항목:
- 총 대상 심볼 수
- 원본 데이터 커버리지(예상 처리 기간): `min_date ~ max_date` (심볼별이 아니라 전체 요약)
- 지표 목록(파라미터 포함)과 지표별 예상 row 수(대략치)
- 총 예상 INSERT row 수(대략치)

예시:
- 총 심볼: 100개
- 예상 처리 기간: 2020-01-01 ~ 2024-12-31
- 지표 목록:
  - rsi(window=14, column=close): ~50,000 rows
  - sma(window=50, column=close): ~50,000 rows
- 총 예상 INSERT: ~100,000 rows

