# 주봉 집계/적재 로직 리팩터링 계획서

**파일**: `docs/weekly_aggregation_refactor_plan.md`

## 0. 요약

현재 `scripts/bulk_update_weekly.py` / `scripts/weekly_update.py`는 모두 `to_period('W-FRI')` 기반으로 주차를 그룹핑하지만,
- `week_start` 컬럼이 “첫 거래일”을 의미하지 않을 수 있고(Period start 사용),
- 최신 주(미완성 가능 주)를 생성/저장해 버릴 수 있으며,
- `weekly_update.py`는 주봉 가격을 UPSERT로 덮어쓰는 정책이라(반면 bulk는 insert-only), 운영 정책이 일관되지 않습니다.

본 계획서는 다음을 목표로 합니다.

- **주봉 가격 생성 규칙 통일**: `week_start=첫 거래일`, `week_end=마지막 거래일`
- **미완성 주 방지**: 입력 데이터의 `max(date)`가 속한 주차는 통째로 스킵(A안)
- **저장 정책 통일**: `weekly_update.py`의 주봉 가격 저장도 insert-only로 변경
- **중복 구현 제거**: 두 스크립트가 동일한 집계 함수를 사용하도록 공통 모듈로 분리

> 전제(사용자 확정): 기존 `stock_prices_weekly`, `stock_indicators_weekly` 데이터는 수동으로 전체 삭제 후 재생성한다.

---

## 1. 현재 코드 근거(현행 동작)

### 1.1 weekly_update가 사용하는 입력 범위
`weekly_update.py`는 심볼별로 아래 범위의 일봉을 DB에서 읽습니다.

- **최근 60주 ≈ 420일**: `start_60weeks = end_date - timedelta(days=420)`
- 조회 SQL: `WHERE date >= :start AND date <= :end ORDER BY date ASC`

즉, “최근 n일”이라는 사용자의 예상은 **현재 로직과 부합**합니다(정확히는 420일).

### 1.2 daily_update의 “최근 30일 insert_only” 보정 시나리오와 주봉 생성
사용자 시나리오:
- 지난주 금요일 daily_update 실패로 금요일 일봉 미적재
- 이번주 월요일 daily_update 성공 시, 최근 30일을 다시 가져와 insert_only로 적재
  - 결과적으로 **지난주 금요일 + 이번주 월요일** 데이터가 모두 적재될 수 있음

현행 `weekly_update.py`는 최근 420일을 읽기 때문에, 위 보정으로 들어온 ‘지난주 금요일’은 당연히 조회 범위에 포함됩니다.
따라서 **(집계/저장 정책만 허용된다면) 지난주 주봉을 생성/보정할 수 있는 입력 데이터는 확보되는 구조**입니다.

다만, 본 리팩터에서 적용할 ‘최신 주차 스킵(A안)’ 때문에 다음이 중요해집니다.

- A안: `max(date)`가 속한 주차는 스킵
- 위 시나리오에서 `max(date)`는 보통 ‘이번주 월요일’이므로,
  - 스킵되는 것은 “이번주(진행중) 주봉”
  - “지난주(완성 주봉)”은 스킵 대상이 아니어서 생성/보정 가능

즉, 사용자 예상은 **A안과도 양립**합니다.

---

## 2. 목표/비목표

### 2.1 목표
1) `bulk_update_weekly.py` / `weekly_update.py` 주봉 집계 규칙 완전 통일
2) `week_start`를 ‘그 주의 첫 거래일’, `week_end`를 ‘그 주의 마지막 거래일’로 저장
3) 미완성 주봉 방지: 입력 데이터의 `max(date)`가 속한 주차는 생성/저장에서 제외(A안)
4) `weekly_update.py`의 **주봉 가격 저장을 insert-only로 변경** (기존 row는 pass)
5) `weekly_update.py`의 **주봉 지표 저장도 insert-only로 변경** (기존 row는 pass)
6) 주봉 지표 누락 방지: **값이 NaN/None인 경우에도 value=NULL row를 저장**하여 “계산됨/미계산됨”을 명확히 구분
7) 집계 로직을 공통 모듈로 분리하여 중복 제거 및 향후 유지보수 비용 감소

### 2.2 비목표
- 주봉 테이블 스키마 변경
- 기존 weekly 데이터 마이그레이션 자동화(사용자가 수동 삭제 예정)

> 참고(현행 코드): `IndicatorPipeline.to_long_dataframe()`는 `dropna(subset=['value'])`를 수행하므로,
> warmup/데이터부족 구간의 지표는 row 자체가 저장되지 않을 수 있습니다.
> 본 리팩터에서는 이 정책을 **전역으로 바꾸지 않고**, `keep_nan` 옵션을 추가해 *weekly_update에서만* NULL 저장을 활성화합니다.

---

## 3. 의사결정(확정 사항)

1) **최신 주차 스킵 기준**: 입력 데이터 `daily_df['date'].max()`가 속한 주차(week key)를 스킵
2) **기존 weekly 데이터 처리**: 리팩터 적용 전, 사용자가 weekly 테이블 데이터를 수동으로 비우고 실행
3) **weekly_update 주봉 가격 저장 정책**: insert-only
4) **weekly_update 주봉 지표 저장 정책**: insert-only
5) **주봉 지표 NULL 저장 정책**: weekly_update에서만 `to_long_dataframe(..., keep_nan=True)`를 사용해 NaN을 NULL로 적재
6) **weekly_update 로드 범위**: 최장 지표 SMA(200) 안전 계산을 위해 최근 250주(≈ 1750일) 범위로 로드

---

## 4. 설계(집계 규칙)

### 4.1 주차 그룹핑 키(week key)
- 주차 그룹핑은 기존처럼 `W-FRI` 기반을 사용한다.
  - 목적: “금요일 종료 주” 기준으로 동일한 주차 묶음 유지

예시(개념):
- 월~금 거래일들이 같은 `W-FRI` period에 속하도록 묶는다.

### 4.2 week_start / week_end 저장 규칙(핵심 변경)
- `week_start`: 해당 주차 그룹 내 **가장 빠른 거래일(date의 min)**
- `week_end`: 해당 주차 그룹 내 **가장 늦은 거래일(date의 max)**

### 4.3 OHLCV 규칙
- open: 그룹 내 첫 거래일 row의 open
- close: 그룹 내 마지막 거래일 row의 close
- high: 그룹 내 high max
- low: 그룹 내 low min
- volume: 그룹 내 volume sum
- adj_close: (존재 시) 그룹 내 마지막 거래일 기준 last

### 4.4 market/source 규칙
- weekly row의 `market`, `source`는 그룹 내 첫 row 기준(first)을 사용(현행 유지)

> 향후 논의: 동일 주차 내 market/source 값이 혼재할 가능성이 있는지(원칙적으로는 없어야 함)

---

## 5. 최신 주차 스킵(A안) 상세

### 5.1 스킵 정의
- `latest_day = daily_df['date'].max()`
- `latest_week_key = latest_day.to_period('W-FRI')`
- 집계 결과 중 `week_key == latest_week_key`에 해당하는 주차는 전부 제거

#### 스킵 적용 시점(확정)
- **스킵은 집계 후(weekly_df 생성 후)에 적용한다.**
  - 즉, `daily_df`는 전체를 사용해 주차 집계를 수행한 뒤,
  - `weekly_df`에서 `week_key == latest_week_key`에 해당하는 row를 drop하여 최신 주차를 제외한다.

### 5.2 기대 효과
- 목요일 밤에 실행해도 ‘이번주 진행중 주봉’이 생성되지 않는다.
- 월요일에 실행해도 ‘이번주 진행중 주봉’이 생성되지 않는다.

---

## 6. 구현 변경 범위(파일별)

### 6.0 공통: to_long_dataframe의 NULL 저장 옵션 추가(대안 A)
- 파일: `indicators/pipeline.py`
- 변경: `IndicatorPipeline.to_long_dataframe()`에 옵션 인자 추가
  - 예시 시그니처:
    - `to_long_dataframe(..., outputs: Dict[str, pd.Series], keep_nan: bool = False) -> pd.DataFrame`
  - 동작:
    - `keep_nan=False`(기본): 기존과 동일하게 `dropna(subset=['value'])`
    - `keep_nan=True`: `dropna`를 하지 않고 NaN을 유지 → DB 적재 시 `value=NULL`로 저장 가능

#### keep_nan=True 저장 규칙(확정)
- `keep_nan=True`인 경우, 저장 전에 **`value` 컬럼의 `np.nan`(또는 `pd.NA`)을 명시적으로 `None`으로 치환**한 뒤 DB에 저장한다.
  - 이유: 드라이버/버전에 따라 `np.nan`이 SQL NULL로 안전하게 변환되지 않을 수 있으므로 명시 치환을 표준으로 둔다.

- 적용 원칙:
  - **weekly_update에서만** `keep_nan=True`
  - daily/bulk/backfill 등 기존 작업은 `keep_nan` 기본값(False)을 유지하여 기존 데이터량/동작을 보존

> 이유
> - NULL 저장 정책을 전역 적용하면 일봉 지표 테이블 row 수가 급증할 수 있어 운영 리스크가 큼
> - weekly_update에만 적용하면 “완료 체크”와 “누락 구분” 목적을 달성하면서 영향 범위를 통제할 수 있음

### 6.1 신규 공통 모듈
- 파일: `core/weekly_aggregation.py` (신규)
- 공개 함수(예시 시그니처):
  - `aggregate_daily_to_weekly_trading_days(daily_df: pd.DataFrame, skip_latest_week: bool = True) -> pd.DataFrame`

#### week_key 정의(확정)
- `week_key` 컬럼은 **`date.to_period('W-FRI')` 값을 그대로 사용**한다.
  - 문자열로 변환하지 않는다(예: `.astype(str)` 금지).
  - 이유: 타입 일관성(Period) 유지로 주차 비교/디버깅을 단순화한다.

### 6.2 bulk_update_weekly.py
- 기존 `aggregate_daily_to_weekly()` 사용처를 공통 모듈 함수로 교체
- insert-only 저장(현재 `INSERT IGNORE`)은 유지
- 실행 범위
  - 현재는 `--start/--end` 또는 DB min/max로 전체 기간 처리
  - 최신 주차 스킵은 심볼 단위로 적용(해당 심볼의 daily_df max(date) 기준)

### 6.3 weekly_update.py
- 기존 `aggregate_daily_to_weekly()` 구현을 제거(또는 미사용 처리)하고 공통 모듈 함수로 교체
- **로드 범위 변경(필수)**
  - 현행: 최근 60주(420일)
  - 변경: 최근 250주(약 1750일)
  - 구현 형태(예시):
    - `start_nweeks = end_date - timedelta(days=250 * 7)`
- 주봉 가격 저장 함수 `save_weekly_prices_upsert()`를 insert-only 방식으로 변경
  - 현 bulk 쪽의 `save_weekly_prices()`와 동일하게 `INSERT IGNORE` 사용
  - 이미 존재하는 `(symbol, week_start)` row는 업데이트하지 않고 pass
- 주봉 지표 저장도 insert-only로 변경
  - `saver.save_long(df_long, mode="insert_only")`
  - 이미 존재하는 `(symbol, week_start, indicator, params_hash)` row는 업데이트하지 않고 pass
- **주봉 지표 NULL 저장 활성화(필수)**
  - `pipeline.to_long_dataframe(..., keep_nan=True)`
  - 목적: 값이 NaN인 구간도 value=NULL row로 저장하여, 주차별 "지표 계산이 시도되었는지"를 DB에서 판별 가능하게 함

---

## 7. 테스트/검증 계획(작업 수행 중 필수)

### 7.1 단위 테스트(로컬, DataFrame 기반)
- 공통 집계 함수에 대해 최소 3케이스를 만든다.

1) 월요일 휴장 케이스
- 입력: 화~금만 존재
- 기대: week_start=화요일, open=화요일 open

2) 금요일 휴장 케이스
- 입력: 월~목만 존재
- 기대: week_end=목요일, close=목요일 close

3) 최신 주차 스킵 케이스
- 2주 데이터가 있고, 마지막 날짜가 포함된 주차는 결과에서 제거됨

### 7.2 통합 검증(DB 기반)
- 전제: 사용자 수행으로 weekly 테이블 비운 후 시작

검증 SQL 예시:
- 주봉의 week_start/week_end가 일봉에 존재하는 거래일인지:

```sql
SELECT w.symbol, w.week_start, w.week_end
FROM stock_prices_weekly w
LEFT JOIN stock_prices d1 ON d1.symbol = w.symbol AND d1.date = w.week_start
LEFT JOIN stock_prices d2 ON d2.symbol = w.symbol AND d2.date = w.week_end
WHERE d1.symbol IS NULL OR d2.symbol IS NULL
LIMIT 50;
```

> 참고: 일부 IDE는 DB 데이터소스가 연결되지 않으면 SQL 코드블록에 경고를 표시할 수 있습니다. 문서 내용 자체의 오류는 아닙니다.

- 최신 주차가 생성되지 않았는지(샘플 심볼 기준):
  - `stock_prices`에서 max(date) 구하고,
  - 그 날짜가 속한 주차의 weekly row가 없는지 확인

---

## 8. 완료 기준(Definition of Done)

- bulk/weekly 두 스크립트 모두 동일한 집계 함수를 사용한다.
- `stock_prices_weekly.week_start`는 해당 주의 첫 거래일이다.
- `stock_prices_weekly.week_end`는 해당 주의 마지막 거래일이다.
- 입력 데이터의 `max(date)`가 포함된 주차 데이터는 weekly 테이블에 생성되지 않는다.
- `weekly_update.py` 주봉 가격 저장은 insert-only이며, 기존 주봉 row를 업데이트하지 않는다.

### 완료 체크(Completion Check) 기준(확정)
- 이번 작업 범위 내에서는 완료 체크를 **"row 수 >= expected spec 수"** 기준으로 유지한다.
  - (현행) `check_weekly_indicators_complete()`가 `COUNT(*) >= expected_count`로 판정
  - 본 리팩터에서 weekly_update는 `keep_nan=True`로 NULL row도 저장하므로,
    row count 기반 완료 체크가 기존보다 안정적으로 동작할 수 있다.

---

## 9. 후속(선택 과제)

- 완료 체크(Completion Check) 로직 고도화
  - 단순 row count 기반이 아니라 (indicator, params_hash) 기대 조합 기반 검증
  - dropna 정책(값이 NaN이면 row가 저장되지 않음)을 고려한 완료 정의 재설계
- `to_long_dataframe()`의 dropna 정책 변경 검토
  - 초기 warmup 구간도 value=NULL row를 저장해 “계산됨/미계산됨”을 명확히 구분
- 주봉 집계/저장에 대한 자동 테스트 phase 추가

> Note: 본 계획에서 weekly_update는 keep_nan=True로 NULL 저장을 수행하므로,
> row count 기반 완료 체크가 기존보다 안정적으로 동작할 수 있다.
