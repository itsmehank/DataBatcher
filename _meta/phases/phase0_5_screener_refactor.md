# P0.5 — 미너비니 스크리너 개편

> 작성일: 2026-04-24  
> 근거 ADR: ADR-009  
> 실행 주체: Builder (Claude Code CLI)  
> 예상 소요: 1~2일  
> 전제: P0 거버넌스 셋업 완료 (`_meta/` 문서 배치 + `CLAUDE.md`/`README.md` 병합 + git commit)

---

## 0. 이 작업은 왜 하는가

Phase 1 LLM 분석 모듈이 "이 종목이 왜 미너비니 템플릿을 통과했는가"를 조건별로 이해할 수 있도록, 스크리너가 **8조건 각각의 통과 여부를 JSON으로 저장**하도록 개편한다.

헌법 §4.2(이해 원칙) 및 ADR-009 참조.

---

## 1. 작업 범위

### 1.1 DB 스키마 변경
- `minervini_screen_results_kr`에 `conditions_met JSON NULL` 컬럼 추가
- `minervini_screen_results_us`에 `conditions_met JSON NULL` 컬럼 추가

### 1.2 코드 변경
- `apps/ingest-databatcher/indicators/minervini/trend_template.py` 리팩토링
- `apps/ingest-databatcher/scripts/kr_minervini_update.py` 수정
- `apps/ingest-databatcher/scripts/us_minervini_update.py` 수정

### 1.3 검증
- 기존 데이터와의 호환성 (backward compatibility) 확인
- 1일치 재실행 후 `conditions_met` 채워지는지 확인
- 기존 프론트엔드 (`trading-view-project`)가 여전히 정상 동작하는지 확인

### 1.4 작업 범위 밖
- 기존 데이터에 소급 백필(backfill)은 **하지 않음**. 당일부터 `conditions_met`가 채워지면 충분. Phase 1은 최신 스크리닝 결과만 사용.
- 저장 정책 변경 (통과 종목만 INSERT) — ADR-008 유지
- `failed_reason` 컬럼 제거 — 건드리지 않음 (ADR-008)

---

## 2. 미너비니 8조건 명세

`_meta/05_GLOSSARY.md` Part B.2의 `conditions_met` 스키마와 정확히 일치해야 함.

| 키 | 의미 | 계산식 |
|---|---|---|
| `price_above_ma150_ma200` | 주가가 150·200일선 위 | `price > sma150 AND price > sma200` |
| `ma150_above_ma200` | 150일선이 200일선 위 | `sma150 > sma200` |
| `ma200_uptrend_1mo` | 200일선이 최소 1개월(약 22거래일) 우상향 | `sma200 > sma200.shift(22)` |
| `ma50_above_ma150_ma200` | 50일선이 150·200일선 위 | `sma50 > sma150 AND sma50 > sma200` |
| `price_above_ma50` | 주가가 50일선 위 | `price > sma50` |
| `price_30pct_above_52w_low` | 주가가 52주 저가 대비 30% 이상 | `price >= low_52w * 1.3` |
| `price_within_25pct_of_52w_high` | 주가가 52주 고가의 75% 이상 | `price >= high_52w * 0.75` |
| `rs_rating_above_70` | RS Rating ≥ 70 | `rs_rating >= 70` (단, `minervini_{kr,us}.filters.rs_rating.min`으로 override 가능) |

**현재 구현과의 차이**:
- 현재 `trend_template.py`의 `ma_ordering` 필터는 `price > sma50 > sma150 > sma200`를 하나의 마스크로 합쳐 평가. 이를 분해하여 `price_above_ma150_ma200`, `ma150_above_ma200`, `ma50_above_ma150_ma200`, `price_above_ma50` 4개 조건으로 쪼갬.
- 나머지 조건(`ma200_uptrend_1mo`, `price_30pct_above_52w_low`, `price_within_25pct_of_52w_high`, `rs_rating_above_70`)은 이미 구현되어 있으나 결과를 개별 저장하지 않음.

**통과 판정**:
- 8조건 중 `rs_rating_above_70`을 제외한 7개는 AND 결합 필수.
- `rs_rating_above_70`은 설정(`filters.rs_rating.enabled`)에 따라 on/off 가능. 현재 설정은 on, min=80. Phase 1 이전에는 기존 설정 유지.
- Blue Dot 옵션은 미너비니 8조건에 포함되지 않음. 현재 `filters.blue_dot.enabled: false`이므로 무관. 필요 시 별도 조건(`conditions_met` 외의 필드)로 유지.

---

## 3. 단계별 실행 절차

### Step 1: 신규 브랜치 생성

```bash
cd DataBatcher
git checkout -b phase0_5/screener-refactor
```

### Step 2: DB 마이그레이션 파일 작성

`apps/ingest-databatcher/scripts/migrations/add_conditions_met_column.sql` 신규 생성:

```sql
-- Date: 2026-04-24
-- ADR-009: Add conditions_met JSON column to store per-condition pass/fail
-- for Minervini trend template screening results.
-- Rationale: Phase 1 LLM analysis needs to know WHICH conditions a stock
-- passed to produce meaningful reasoning.

ALTER TABLE minervini_screen_results_kr
  ADD COLUMN conditions_met JSON NULL COMMENT 'ADR-009: per-condition pass/fail map'
  AFTER is_blue_dot;

ALTER TABLE minervini_screen_results_us
  ADD COLUMN conditions_met JSON NULL COMMENT 'ADR-009: per-condition pass/fail map'
  AFTER is_blue_dot;
```

### Step 3: 마이그레이션 실행

먼저 현재 프로덕션 DB 상태 확인 + 백업:

```bash
# 스키마 확인
mysql -u $DB_USER -p$DB_PASSWORD -e "DESCRIBE market.minervini_screen_results_kr;"
mysql -u $DB_USER -p$DB_PASSWORD -e "DESCRIBE market.minervini_screen_results_us;"

# 월간 백업이 최근인지 확인 (ops/shell/db_backup_monthly.sh 로그)
```

마이그레이션 실행:

```bash
mysql -u $DB_USER -p$DB_PASSWORD market < apps/ingest-databatcher/scripts/migrations/add_conditions_met_column.sql

# 적용 확인
mysql -u $DB_USER -p$DB_PASSWORD -e "DESCRIBE market.minervini_screen_results_kr;" | grep conditions_met
mysql -u $DB_USER -p$DB_PASSWORD -e "DESCRIBE market.minervini_screen_results_us;" | grep conditions_met
```

### Step 4: `trend_template.py` 리팩토링

`apps/ingest-databatcher/indicators/minervini/trend_template.py`를 아래와 같이 확장.

**기존 함수 시그니처는 유지** (backward compatibility). 새 함수 추가 또는 기존 함수 반환값 확장.

권장 방식: 기존 함수가 반환하는 `(pass_mask, failed_reasons)` 튜플 뒤에 새로운 3번째 요소 `conditions_dict`를 추가 반환. 기존 호출자가 튜플 언팩킹을 `a, b = ...`로 쓰고 있다면 `a, b, _ = ...`로 바꾸거나 새 변수 추가.

**더 안전한 대안**: 새 함수 `screen_minervini_trend_template_detailed()`를 추가하고 기존 함수는 유지. 업데이트 스크립트만 새 함수로 이동.

```python
# indicators/minervini/trend_template.py
from __future__ import annotations
import pandas as pd


def _compute_condition_masks(
    prices_wide: pd.DataFrame,
    rs_rating_wide: pd.DataFrame | None,
    config: dict,
) -> dict[str, pd.DataFrame]:
    """
    Compute all 8 Minervini trend template conditions as separate boolean masks.
    Returns a dict mapping condition key -> (dates × symbols) boolean DataFrame.
    Condition keys match _meta/05_GLOSSARY.md Part B.2 `conditions_met` schema.
    """
    sma_50 = prices_wide.rolling(window=50, min_periods=50).mean()
    sma_150 = prices_wide.rolling(window=150, min_periods=150).mean()
    sma_200 = prices_wide.rolling(window=200, min_periods=200).mean()

    lookback_52w = config.get("lookback_52w", 252)
    high_52w = prices_wide.rolling(window=lookback_52w, min_periods=lookback_52w).max()
    low_52w = prices_wide.rolling(window=lookback_52w, min_periods=lookback_52w).min()

    filters = config.get("filters", {})
    sma200_uptrend_lookback = filters.get("sma200_uptrend", {}).get("lookback", 22)
    low_pct = filters.get("price_above_52w_low", {}).get("pct", 1.3)
    high_pct = filters.get("price_near_52w_high", {}).get("pct", 0.75)
    rs_min = filters.get("rs_rating", {}).get("min", 70)

    conditions: dict[str, pd.DataFrame] = {}

    # 1. Price above MA150 and MA200
    conditions["price_above_ma150_ma200"] = (prices_wide > sma_150) & (prices_wide > sma_200)

    # 2. MA150 above MA200
    conditions["ma150_above_ma200"] = sma_150 > sma_200

    # 3. MA200 uptrend (1 month)
    conditions["ma200_uptrend_1mo"] = sma_200 > sma_200.shift(sma200_uptrend_lookback)

    # 4. MA50 above MA150 and MA200
    conditions["ma50_above_ma150_ma200"] = (sma_50 > sma_150) & (sma_50 > sma_200)

    # 5. Price above MA50
    conditions["price_above_ma50"] = prices_wide > sma_50

    # 6. Price at least 30% above 52-week low
    conditions["price_30pct_above_52w_low"] = prices_wide >= (low_52w * low_pct)

    # 7. Price within 25% of 52-week high
    conditions["price_within_25pct_of_52w_high"] = prices_wide >= (high_52w * high_pct)

    # 8. RS Rating above threshold
    if rs_rating_wide is not None and not rs_rating_wide.empty:
        rs_aligned = rs_rating_wide.reindex_like(prices_wide)
        conditions["rs_rating_above_70"] = rs_aligned >= rs_min
    else:
        conditions["rs_rating_above_70"] = pd.DataFrame(
            False, index=prices_wide.index, columns=prices_wide.columns
        )

    return conditions


def screen_minervini_trend_template(
    prices_wide: pd.DataFrame,
    rs_rating_wide: pd.DataFrame | None,
    blue_dot_wide: pd.DataFrame | None,
    config: dict,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, pd.DataFrame]]:
    """
    Minervini Trend Template screening.
    Returns:
        pass_mask: (dates × symbols) bool DataFrame — overall pass
        failed_reasons: empty DataFrame (placeholder, kept for backward compat)
        conditions: dict of condition_key -> (dates × symbols) bool DataFrame
                    for all 8 conditions (and optional blue_dot if enabled)
    """
    if prices_wide.empty:
        return pd.DataFrame(), pd.DataFrame(), {}

    filters = config.get("filters", {})
    conditions = _compute_condition_masks(prices_wide, rs_rating_wide, config)

    # Determine which conditions are active based on config (for overall pass_mask)
    # NOTE: conditions dict always contains all 8 conditions regardless of filter toggles,
    # so LLM/audit can see full structure. The pass_mask respects filter toggles.
    active_masks: list[pd.DataFrame] = []

    if filters.get("ma_ordering", {}).get("enabled", True):
        # ma_ordering composes conditions 1, 2, 4, 5
        active_masks.append(conditions["price_above_ma150_ma200"])
        active_masks.append(conditions["ma150_above_ma200"])
        active_masks.append(conditions["ma50_above_ma150_ma200"])
        active_masks.append(conditions["price_above_ma50"])
    if filters.get("sma200_uptrend", {}).get("enabled", True):
        active_masks.append(conditions["ma200_uptrend_1mo"])
    if filters.get("price_above_52w_low", {}).get("enabled", True):
        active_masks.append(conditions["price_30pct_above_52w_low"])
    if filters.get("price_near_52w_high", {}).get("enabled", True):
        active_masks.append(conditions["price_within_25pct_of_52w_high"])
    if filters.get("rs_rating", {}).get("enabled", True):
        active_masks.append(conditions["rs_rating_above_70"])

    # Optional Blue Dot (not part of 8 conditions, kept as separate filter)
    if filters.get("blue_dot", {}).get("enabled", False):
        if blue_dot_wide is not None and not blue_dot_wide.empty:
            bd_aligned = blue_dot_wide.reindex_like(prices_wide)
            active_masks.append(bd_aligned == 1)
        else:
            active_masks.append(
                pd.DataFrame(False, index=prices_wide.index, columns=prices_wide.columns)
            )

    if not active_masks:
        pass_mask = pd.DataFrame(True, index=prices_wide.index, columns=prices_wide.columns)
    else:
        pass_mask = active_masks[0]
        for m in active_masks[1:]:
            pass_mask = pass_mask & m

    return pass_mask, pd.DataFrame(), conditions
```

### Step 5: `kr_minervini_update.py` / `us_minervini_update.py` 수정

기존 호출부를 3-tuple 언팩킹으로 변경하고, 통과 종목 각각의 `conditions_met`을 JSON으로 저장.

핵심 변경 위치 (KR 기준, US도 동일 패턴):

```python
# 기존
pass_mask, _ = screen_minervini_trend_template(
    prices_wide=prices_wide,
    rs_rating_wide=rs_rating_wide,
    blue_dot_wide=blue_dot_wide,
    config=minervini_cfg,
)

# 신규
pass_mask, _, conditions = screen_minervini_trend_template(
    prices_wide=prices_wide,
    rs_rating_wide=rs_rating_wide,
    blue_dot_wide=blue_dot_wide,
    config=minervini_cfg,
)
```

그리고 통과 레코드 생성 직전에, 각 (symbol, date) 쌍에 대해 `conditions_met` dict를 만들어 JSON 직렬화. 예:

```python
import json

# melted: 통과 종목만 뽑힌 long-form DataFrame (symbol, date, market, rs_rating, is_blue_dot)
# conditions: dict of condition_key -> wide DataFrame (dates × symbols)

def _build_conditions_met(symbol: str, date, conditions: dict[str, pd.DataFrame]) -> str:
    """Build conditions_met JSON string for a given (symbol, date)."""
    result = {}
    for key, mask_df in conditions.items():
        try:
            val = mask_df.at[date, symbol]
            # NaN 처리: pd.isna면 False로 (인디케이터 미산출 구간)
            if pd.isna(val):
                result[key] = False
            else:
                result[key] = bool(val)
        except KeyError:
            result[key] = False
    return json.dumps(result)

# melted에 컬럼 추가
melted["conditions_met"] = melted.apply(
    lambda row: _build_conditions_met(row["symbol"], row["date"], conditions),
    axis=1,
)

# 저장할 컬럼에 추가
result_df = melted[[
    "symbol", "date", "market", "rs_rating", "is_blue_dot",
    "conditions_met", "screen_config_hash", "failed_reason"
]]
```

주의:
- `mask_df.at[date, symbol]`에서 `date`는 pandas Timestamp 또는 index가 일치하는 형태여야 함. 실제 코드에서 날짜 타입 정렬 확인 필요.
- NaN 처리: 52주 구간 미충족으로 `low_52w`/`high_52w`가 NaN인 경우, 해당 조건은 `False`로 기록 (통과 불가).
- `apply(axis=1)`이 대량 데이터에서 느리면 벡터 연산으로 최적화. 우선은 정확성·가독성 우선.

### Step 6: 로컬 테스트

```bash
# 1. 기존 테스트가 깨지지 않는지 확인
pytest -q apps/ingest-databatcher/tests apps/ingest-databatcher/scripts/tests

# 2. 문법 검증
python -m compileall apps/ingest-databatcher/indicators apps/ingest-databatcher/scripts

# 3. 소규모 실행 (test DB 권장)
export DATABASE_URL="mysql+pymysql://user:pass@127.0.0.1:3306/trade_test?charset=utf8mb4"
python apps/ingest-databatcher/scripts/kr_minervini_update.py --days 3 --force

# 4. 결과 확인: conditions_met이 채워졌는가?
mysql -u $DB_USER -p$DB_PASSWORD -e "
  SELECT symbol, date, market, conditions_met
  FROM trade_test.minervini_screen_results_kr
  WHERE conditions_met IS NOT NULL
  ORDER BY date DESC, symbol
  LIMIT 5;
"

# 5. JSON 구조가 GLOSSARY 스키마와 일치하는가?
#    - 8개 키가 모두 존재
#    - 모든 값이 boolean (true/false)
#    - 통과 종목이므로 filter로 enable된 조건은 모두 true
```

### Step 7: US 스크립트에 동일 변경 적용

`us_minervini_update.py`도 `kr_minervini_update.py`와 동일한 패턴으로 수정. 동일 테스트 반복.

### Step 8: 기존 프론트엔드 동작 확인

`trading-view-project` 백엔드/프론트엔드가 여전히 정상 동작하는지 확인. 새 컬럼을 사용하지 않으므로 영향 없어야 함.

```bash
# trading-view-project 실행
cd apps/trading-view-project
bash run-dev.sh

# 브라우저에서 Dashboard/ListView/ChartView 접속해서
# KR/US 각 region의 minervini 결과가 정상 조회되는지 확인
```

### Step 9: 프로덕션 적용

테스트 DB에서 검증 완료 후 프로덕션 DB에 마이그레이션 실행:

```bash
# 프로덕션 DB에 ALTER 적용
mysql -u $DB_USER -p$DB_PASSWORD market < apps/ingest-databatcher/scripts/migrations/add_conditions_met_column.sql

# 1일치 재실행 (프로덕션 DB)
python apps/ingest-databatcher/scripts/kr_minervini_update.py --days 1 --force
python apps/ingest-databatcher/scripts/us_minervini_update.py --days 1 --force

# 결과 확인
```

### Step 10: commit + PR 머지

```bash
git add apps/ingest-databatcher/indicators/minervini/trend_template.py
git add apps/ingest-databatcher/scripts/kr_minervini_update.py
git add apps/ingest-databatcher/scripts/us_minervini_update.py
git add apps/ingest-databatcher/scripts/migrations/add_conditions_met_column.sql
git commit -m "feat(screener): add conditions_met JSON per ADR-009

- Refactor trend_template.py to compute 8 Minervini conditions separately
- Add conditions_met JSON column to minervini_screen_results_kr/us
- Update KR/US minervini update scripts to save per-condition pass/fail
- Prepare data structure for Phase 1 LLM analysis input

Relates to ADR-009."
```

---

## 4. 검증 체크리스트

작업 완료 시점에 모두 체크되어야 함:

- [ ] `minervini_screen_results_kr/us`에 `conditions_met` 컬럼이 존재
- [ ] `trend_template.py`의 `screen_minervini_trend_template()`가 3-tuple 반환
- [ ] 새 `_compute_condition_masks()` 헬퍼 함수 존재
- [ ] KR/US 업데이트 스크립트가 `conditions_met` JSON을 저장
- [ ] 통과 종목의 `conditions_met`에 8개 키가 모두 존재
- [ ] 통과 종목의 `conditions_met` 값이 모두 `true` (enable된 조건에 대해)
- [ ] 기존 pytest 전부 통과
- [ ] `trading-view-project` Dashboard/ListView/ChartView가 정상 조회
- [ ] 프로덕션 DB에 마이그레이션 적용 완료
- [ ] 프로덕션 DB에 1일치 신규 데이터 `conditions_met` 채워짐
- [ ] commit + merge 완료

---

## 5. Builder에게 전달할 프롬프트 (Claude Code CLI용)

아래를 Claude Code CLI의 첫 프롬프트로 사용:

```
_meta/phases/phase0_5_screener_refactor.md를 읽고,
그 문서의 §3 단계별 실행 절차를 순서대로 수행해줘.

각 Step을 시작하기 전에 무엇을 할지 간단히 요약하고,
Step이 끝나면 검증 결과를 보고해줘.

Step 3(프로덕션 DB 마이그레이션)과 Step 9(프로덕션 적용)는
위험한 작업이니 반드시 내 승인을 받은 후에 실행해줘.
테스트 DB 작업은 사전 승인 없이 진행해도 돼.

작업 중 `_meta/` 문서와 실제 코드 사이에 불일치를 발견하면
수정하지 말고 보고만 해줘. (ADR-005 및 CLAUDE.md 거버넌스 섹션 참조)
```

---

## 6. 작업 완료 후

이 작업이 끝나면:

1. `_meta/06_CURRENT_STATE.md` 갱신 — "P0.5 완료" 기록 (Architect 세션)
2. Phase 1 brief 작성 시작 — `_meta/phases/phase1_brief.md` (Architect 세션)
3. Phase 1 Builder 세션은 brief 확정 후 시작

---

*이 가이드는 ADR-009의 "스크리너 개편을 Phase 1 시작 전에 수행" 결정을 실행하기 위한 체크리스트다.*