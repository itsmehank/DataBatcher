# Phase 1 Brief — LLM 분석 레이어 구축

> 작성일: 2026-04-24 (초안), 2026-04-26 (§7.2·§8·§10·§11 통합 갱신)  
> 작성자: Architect (Web Claude session)  
> 상태: Draft (사용자 승인 대기 → 승인 시 Builder 세션에서 단계별 실행)  
> 관련 ADR: ADR-001, ADR-002, ADR-003, ADR-004, ADR-005, ADR-009, ADR-010, ADR-011, ADR-012  
> 선행 조건: P0.5 완료 (✅), 운영 환경 Q-001 적용 완료 (✅ 2026-04-26 18:18 KST)

---

## 목차

- §1. 목표와 종료 조건
- §2. 범위 (In/Out)
- §3. 단계별 작업 (1.1, 1.2, 1.3)
- §4. 데이터 인터페이스 — 마이그레이션 3종 산출물
- §5. 새 앱 디렉토리 구조
- §6. 프롬프트 설계 (가장 깊은 논의 필요)
- §7. 비용·상한·에러·재시도 정책
- §8. 배치 통합 방식
- §9. 검증·승인 기준
- §10. Builder 세션에 전달할 프롬프트
- §11. 미해결 질문 / Phase 1 후로 미루는 것

---

## §1. 목표와 종료 조건

### 1.1 목표

미너비니 트렌드 템플릿을 통과한 종목에 대해 LLM이 자동으로 차트 분석을 수행하고, **`entry / watch / ignore` 분류**를 내리며, **`entry`로 판정된 종목에 진입가·손절가·제안 비중**을 산출하는 모듈을 구축한다.

이 모듈은:
- 매일 daily cron 흐름의 일부로 자동 실행됨
- 결과를 `daily_analysis_kr/us` 테이블에 구조화된 형태로 저장
- 모든 LLM 호출을 `llm_calls` 테이블에 영구 기록 (헌법 §2.5)
- 사용자 승인 게이트 없이는 실제 매매로 이어지지 않음 (헌법 §2.1)

### 1.2 종료 조건 (정성적 기준 — 점검 1=A)

다음 모두 충족 시 Phase 1 종료:

1. ✅ **자동 실행**: 매일 daily cron이 (3) 미너비니 스크리닝 직후 (5) 분석·분류와 (6) 진입 파라미터 산출을 자동 실행한다.
2. ✅ **구조화 저장**: `daily_analysis_kr`, `daily_analysis_us`에 결과가 누적된다. `llm_calls`에 모든 호출 로그가 남는다.
3. ✅ **품질 검토**: 사용자가 **최소 7거래일치 결과**를 직접 검토하고 "이 정도면 쓸만하다"고 정성적으로 판단한다.
4. ✅ **헌법 준수**: 이 Phase에서 도입된 모든 코드가 헌법 §2.1, §2.2, §2.5를 위반하지 않는다 (Auditor 세션이 확인).
5. ✅ **운영 큐**: 본 Phase의 마이그레이션이 운영 환경에 적용 완료(Q 항목이 "완료" 섹션에 이동).

### 1.3 비-종료 조건 (이걸로는 종료 판단 안 함)

- 백테스트 정량 성과 → Phase 5
- 사용자 시간 부담 측정 → Phase 2(메일) 이후
- 비용 절대값 → 모니터링은 하지만 임계값 통과 자체가 종료 기준은 아님

---

## §2. 범위 (In/Out)

### 2.1 In Scope (이 Phase에서 한다)

- **(5) `analyze_chart()`**: 종목 1개 → 분류·근거·패턴·리스크 플래그 (구조화 JSON)
- **(6) `calculate_entry_params()`**: (5)에서 entry로 판정된 종목 → 진입가·손절가·비중·기대 타겟
- **DB 스키마**: `daily_analysis_kr`, `daily_analysis_us`, `llm_calls` 신설 (ADR-009 명세)
- **새 앱**: `apps/llm-analysis/` 디렉토리 신설
- **배치 통합**: 기존 daily cron의 `kr_minervini_update.py` / `us_minervini_update.py` 직후 분석 실행
- **로깅·관측**: 호출 로그 + 일일 비용·호출 수 합계 보고
- **상한·캐싱**: 일일 호출 상한 + 결과 캐싱 (재호출 방지)
- **CLI 도구**: 수동 실행, 백필, 단일 종목 디버깅용

### 2.2 Out of Scope (이 Phase에서 안 한다)

- **Crypto 분석** (점검 2=A) — 별도 Phase에서 결정
- **장중 실시간 분석** (ADR-004) — 영구 비목표
- **백테스트** — Phase 5
- **이메일 발송** — Phase 2
- **AI 카드 UI** — Phase 3
- **Q&A 에이전트** — Phase 4
- **52주 고가/저가·volume_ma20의 인디케이터 영구화** — Phase 1 LLM 호출부에서 즉석 계산. Phase 5 백테스트 시 재검토.
- **다중 모델 비교 / A·B 테스트** — Phase 5 또는 별도 R&D
- **프롬프트 자동 진화 / RLHF** — 영구 비목표 (헌법 §4.1 통제권)

### 2.3 Assumptions (전제)

- ANTHROPIC_API_KEY가 환경 변수로 셋업됨 (`.env`에 추가)
- 운영 환경의 `kr_minervini_update.py` / `us_minervini_update.py`가 정상 작동 중 (P0.5 commit이 운영에 반영된 후)
- 일일 entry 후보가 KR 50개, US 50개 이내 (실제로는 보통 더 적음)
- LLM 호출 평균 지연 5~15초, 일일 분석 100건 기준 약 8~25분 소요 (직렬 처리 시)

---

## §4. 데이터 인터페이스 — 마이그레이션 3종 산출물

ADR-010에 따라 본 Phase의 모든 스키마 변경은 ① Alembic ② raw SQL ③ 운영 큐 항목 세 가지를 함께 만든다.

### 4.1 신규 테이블 1: `daily_analysis_kr`

스키마는 GLOSSARY Part B.1.7에 정의됨. 그대로 인용:

```sql
CREATE TABLE daily_analysis_kr (
  symbol             VARCHAR(32)  NOT NULL,
  date               DATE         NOT NULL,
  market             VARCHAR(16)  NOT NULL,
  classification     VARCHAR(20)  NOT NULL,    -- 'entry' | 'watch' | 'ignore'
  confidence         DECIMAL(3,2) NULL,
  reasoning          TEXT         NULL,
  pattern            VARCHAR(50)  NULL,
  risk_flags         JSON         NULL,
  entry_params       JSON         NULL,        -- entry 분류일 때만
  screen_config_hash CHAR(40)     NULL,
  llm_call_id        BIGINT       NULL,
  created_at         TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (symbol, date),
  KEY idx_date_class (date, classification),
  KEY idx_date_market (date, market)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 4.2 신규 테이블 2: `daily_analysis_us`

`daily_analysis_kr`과 동일 구조. `market` 값만 NYSE/NASDAQ/ETF.

### 4.3 신규 테이블 3: `llm_calls`

스키마는 GLOSSARY Part B.1.7에 정의됨. 그대로 인용:

```sql
CREATE TABLE llm_calls (
  id                BIGINT PRIMARY KEY AUTO_INCREMENT,
  timestamp         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  module            VARCHAR(50),
  model             VARCHAR(50),
  prompt_tokens     INT,
  completion_tokens INT,
  cost_usd          DECIMAL(10,6),
  request_payload   JSON,
  response_payload  JSON,
  duration_ms       INT,
  error             TEXT NULL,
  KEY idx_timestamp (timestamp),
  KEY idx_module_timestamp (module, timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 4.4 마이그레이션 산출물

**Alembic 파일** (필수):
- `db/migrations/versions/YYYYMMDD_NNNNNN_add_daily_analysis_and_llm_calls.py`
- 세 테이블을 한 마이그레이션으로 묶을 것

**Raw SQL 파일** (필수, 사람 검토용):
- `apps/ingest-databatcher/scripts/migrations/add_daily_analysis_and_llm_calls.sql`
- 위 ALTER 없이 CREATE 3개

**운영 큐 항목** (필수):
- `_meta/operational_queue.md`의 "대기 중인 작업"에 **Q-002** 추가
- Q-001과 동일한 양식 — PowerShell 명령, 백업, 검증, 타이밍 윈도우

### 4.5 `daily_analysis_*.classification` 값 정의

- **`entry`**: 지금 진입 후보. (6) `calculate_entry_params()`가 이어서 호출됨.
- **`watch`**: 지금 진입 부적절하지만 베이스 형성 중. 1~4주 내 재평가 가치 있음.
- **`ignore`**: 미너비니 관점에서 진입 부적합. (예: 베이스 부족, 추세 약함, 리스크 과다)

LLM이 셋 중 정확히 하나를 출력해야 함 (구조화 JSON 강제).

### 4.6 `daily_analysis_*.confidence`

0.00 ~ 1.00. LLM의 자체 확신도. classification과 함께 출력.

용도:
- 모니터링 (낮은 confidence가 많이 나오면 프롬프트 또는 입력 데이터 점검)
- 향후 정렬 (대시보드에서 confidence 높은 순으로 표시)

이 값은 **사용자 의사결정에 직접 쓰지 않음**. 사용자는 reasoning을 봐야 한다.

### 4.7 `risk_flags` 사용

GLOSSARY Part B.2의 7개 플래그. LLM이 해당하는 것만 배열로 출력:
```json
["high_rs_rating", "extended_from_ma50"]
```

### 4.8 `entry_params` JSON 스키마

GLOSSARY Part B.2 그대로. (5)에서 채우지 않음. (6)에서만 채움.

### 4.9 `screen_config_hash` 추적

`daily_analysis_*` 행이 만들어질 때, 그 시점의 `minervini_screen_results_*.screen_config_hash`를 함께 저장. 이유:
- 스크리너 설정이 바뀌었을 때 분석 결과를 정확히 어느 설정 기준으로 만든 건지 추적
- Phase 5 백테스트 시 재현성 확보

---

## §5. 새 앱 디렉토리 구조 — `apps/llm-analysis/`

### 5.1 명명

`apps/llm-analysis/` (점검 6 결정).

기존 패턴(`ingest-databatcher`, `trading-view-project`)과 일관. "llm"이 들어가 있어 헌법 §2.2 (결정론 코어와 LLM 분석 레이어 물리적 분리)와 시각적으로도 부합.

### 5.2 디렉토리 구조

````
apps/llm-analysis/
├── README.md                       # 이 앱의 목적·사용법
├── pyproject.toml or requirements.txt   # 패키지 의존성
├── .env.example                    # 환경 변수 템플릿
│
├── config/
│   └── settings.yaml               # 일일 상한, 모델, 프롬프트 버전 등
│
├── core/
│   ├── __init__.py
│   ├── anthropic_client.py         # Anthropic API 호출 + llm_calls 기록 wrapper
│   ├── data_loader.py              # 분석 대상 종목·차트 데이터 DB 조회
│   ├── prompt_builder.py           # 입력 → 프롬프트 페이로드 직렬화
│   ├── result_parser.py            # LLM 응답 → AnalysisResult / EntryParams Pydantic 모델
│   └── cost_tracker.py             # 일일 호출 수·비용 집계
│
├── models/
│   ├── __init__.py
│   ├── analysis_result.py          # AnalysisResult (Pydantic)
│   └── entry_params.py             # EntryParams (Pydantic)
│
├── prompts/
│   ├── analyze_chart_v1.md         # (5) 프롬프트 본문
│   └── calculate_entry_params_v1.md  # (6) 프롬프트 본문
│
├── scripts/
│   ├── run_daily_analysis.py       # 메인 진입점 (배치에서 호출)
│   ├── run_single_symbol.py        # 단일 종목 디버깅
│   ├── backfill_analysis.py        # 과거 분석 결과 보충 (사용 빈도 낮음)
│   └── show_cost_summary.py        # 일일/주간/월간 비용 리포트
│
└── tests/
    ├── test_prompt_builder.py
    ├── test_result_parser.py
    └── test_anthropic_client.py    # API mocking
````

### 5.3 `apps/ingest-databatcher/`와의 관계

**`llm-analysis`가 `ingest-databatcher`를 함수 호출하지 않는다** — 헌법 §2.2 준수.

대신 **DB를 통해 데이터만 읽음**:
- `minervini_screen_results_kr/us` (입력)
- `stock_prices`, `us_stock_prices`, `stock_indicators`, `us_stock_indicators`, weekly 버전 (입력 차트 데이터)
- `symbol_master`, `us_symbol_master` (섹터 정보)
- `daily_analysis_kr/us`, `llm_calls` (출력)

각 앱은 독립적으로 실행 가능 + 한쪽 장애가 다른 쪽으로 전파 안 됨.

### 5.4 `config/settings.yaml` 초안

````yaml
# apps/llm-analysis/config/settings.yaml

# 데이터베이스 (ingest-databatcher와 동일한 DB 사용)
database:
  url: ${DATABASE_URL}    # 환경 변수 우선

# Anthropic API
anthropic:
  model_analysis: "claude-sonnet-4-5"   # (5) 차트 분석용 (Sonnet 4.5/4.6 등 시점에 맞춤)
  model_entry: "claude-sonnet-4-5"      # (6) 진입 파라미터용
  temperature: 0
  max_tokens: 2000
  timeout_seconds: 60
  
  # 재시도 정책
  retry:
    max_attempts: 3
    backoff_base_sec: 2
    backoff_max_sec: 30

# 일일 호출 상한 (점검 3 결정)
daily_call_limits:
  enabled: true
  kr: 50            # KR 분석 한도 (entry 후보 + watch 후보 합계)
  us: 50            # US 분석 한도
  hard_stop_on_exceed: true   # true: 한도 초과 시 중단. false: 경고만 로그.

# 비용 알림 임계값
cost_alerts:
  daily_threshold_usd: 5.00     # 하루 비용이 이 값 넘으면 sync_log에 경고 기록
  monthly_threshold_usd: 60.00  # 월 누적 비용 알림

# 결과 캐싱
caching:
  skip_if_exists: true          # 같은 (symbol, date)에 이미 결과 있으면 재호출 안 함
  force_recompute_flag: "--force-recompute"

# 분석 모듈 활성화 (킬 스위치)
modules:
  analyze_chart: true           # (5) 활성화 여부
  calculate_entry_params: true  # (6) 활성화 여부

# 프롬프트 버전
prompts:
  analyze_chart: "v1"           # apps/llm-analysis/prompts/analyze_chart_{version}.md 참조
  calculate_entry_params: "v1"

# 입력 데이터 범위
input_data:
  daily_lookback_days: 252      # 일봉 1년치
  weekly_lookback_weeks: 156    # 주봉 3년치 (장기 베이스 인식용)
  include_indicators: ["sma_50_close", "sma_150_close", "sma_200_close", "rs_line"]
  include_conditions_met: true  # P0.5에서 추가된 conditions_met JSON 포함
  include_sector: true          # symbol_master.sector
````

### 5.5 CLI override (점검 3 보충 결정)

`run_daily_analysis.py`는 YAML 값을 기본으로 쓰되 다음 인자로 override:

````bash
python apps/llm-analysis/scripts/run_daily_analysis.py \
  --region KR \
  --date 2026-04-25 \
  --limit 30 \                  # daily_call_limits.kr override
  --force-recompute \           # caching.skip_if_exists 무시
  --dry-run                     # LLM 호출 안 하고 어떤 종목이 분석 대상인지만 출력
````

`--dry-run`은 디버깅·비용 시뮬레이션에 유용. brief에 명시.

---

## §6. 프롬프트 설계 — Phase 1의 핵심

### 6.1 프롬프트 형식 결정

**점검 5에서 미정으로 남았던 부분.** 여기서 결정한다.

**결정: 텍스트 기반 (옵션 A)** — 이미지 미포함.

근거:
- **비용**: Vision API는 텍스트 대비 토큰당 더 비싸고, 이미지 인풋은 토큰 변환 시 큰 분량을 차지함. 일일 100건 × 차트 이미지 = 비용이 ADR-003 예상치(월 $20~40)를 크게 웃돌 위험.
- **재현성**: 텍스트 입력은 결정론적이고 디버깅 쉬움. 이미지 렌더링이 들어가면 차트 라이브러리 버전·해상도·matplotlib 옵션이 결과에 영향.
- **저장 용량**: `llm_calls.request_payload`에 텍스트는 KB 단위, 이미지 base64는 MB 단위. 헌법 §2.5의 "영구 보존"이 부담스러워짐.
- **속도**: 텍스트 분석이 일반적으로 더 빠름.
- **충분성**: 미너비니의 8조건은 본질적으로 수치 기반이고, RS Rating·SMA·`conditions_met`이 이미 텍스트로 잘 표현됨. 차트 패턴(VCP·flat base·cup with handle)을 보려면 OHLCV 시계열 텍스트로 충분.

**향후 재검토 가능성**:
- Phase 5 백테스트에서 텍스트 분석 정확도가 부족하다고 판명되면 그때 vision API 도입 검토.
- 일단 Phase 1은 텍스트로 시작.

### 6.2 (5) `analyze_chart()` 프롬프트 설계

#### 입력 페이로드 구성

````
{
  "task": "minervini_chart_analysis",
  "symbol": "AAPL",
  "market": "NASDAQ",
  "date": "2026-04-25",
  "sector": "Technology",
  "industry": "Consumer Electronics",
  
  "screen_config_hash": "a1b2c3...",
  "conditions_met": {
    "price_above_ma150_ma200": true,
    "ma150_above_ma200": true,
    "ma200_uptrend_1mo": true,
    "ma50_above_ma150_ma200": true,
    "price_above_ma50": true,
    "price_30pct_above_52w_low": true,
    "price_within_25pct_of_52w_high": true,
    "rs_rating_above_70": true
  },
  
  "rs_rating": 89.0,
  "is_blue_dot": false,
  
  "current_metrics": {
    "close": 187.43,
    "high_52w": 195.82,
    "low_52w": 142.10,
    "pct_from_52w_high": -4.28,
    "pct_above_52w_low": 31.90,
    "volume_ma20": 52341000,
    "volume_today": 48120000,
    "volume_ratio": 0.92
  },
  
  "daily_ohlcv_recent_60d": [
    {"date": "2026-02-25", "open": 182.50, "high": 184.10, "low": 181.30, "close": 183.20, "volume": 51230000},
    ...
  ],
  
  "weekly_ohlcv_recent_52w": [
    {"week_start": "2025-04-28", "open": 165.10, "high": 172.30, "low": 162.50, "close": 168.40, "volume": 248910000},
    ...
  ],
  
  "indicators_recent_60d": [
    {"date": "2026-02-25", "sma_50": 178.20, "sma_150": 165.40, "sma_200": 158.90, "rs_line": 1.082},
    ...
  ]
}
````

토큰 수 추정: 약 8000~12000 tokens input. Anthropic Sonnet 기준 ~$0.03~0.04/호출 input. 출력 ~500 tokens × $0.015/1K = ~$0.0075. **호출당 평균 $0.04** 수준.

100건/일 × 30일 = 3000건/월 × $0.04 = **월 $120** 정도.  
ADR-003의 "$20~40" 추정보다 높음. (5)만 해도 ~$120, (6)은 entry 비율 30%면 추가 ~$36 = **월 $150 안팎**.

> 비용 재추정 결과를 ADR-003에 반영할지, 아니면 입력 데이터를 줄여 비용을 낮출지 — Phase 1 1.1 단계 검증 후 결정. 일단 brief는 위 페이로드로 진행.

#### 프롬프트 본문 (`prompts/analyze_chart_v1.md`)

````markdown
You are a Mark Minervini-style technical analyst. Your task is to classify a single stock as one of `entry`, `watch`, or `ignore` based on Minervini's trend template and base-pattern principles.

## Definitions

- **entry**: Stock is at or near a proper buy point with a clean base. A swing trade entry is appropriate now or imminently (within ~5 trading days).
- **watch**: Stock passes the trend template but is not at a buy point. Either base is forming, or it has extended too far from a recent breakout. Re-evaluation in 1–4 weeks is appropriate.
- **ignore**: Despite passing the trend template, this stock is not a Minervini-quality setup. Examples: thin or wide-and-loose base, climax run, late-stage advance, RS Rating barely passing.

## Inputs

You will receive a JSON payload with:
- Identifier (symbol, market, sector, industry, date)
- Minervini screening results (`conditions_met`: 8 boolean conditions, `rs_rating`, `is_blue_dot`)
- Current price metrics (close, 52w high/low, distance from extremes, volume averages)
- Recent daily OHLCV (~60 trading days)
- Recent weekly OHLCV (~52 weeks for base-pattern recognition)
- Recent indicator series (SMA-50/150/200, RS Line)

## Analysis Procedure

1. **Trend confirmation**: All 8 `conditions_met` should be true (they always will be — the stock has already passed). Check whether each condition passed comfortably or marginally.

2. **Stage analysis**: Identify the current stage (Stage 1 base, Stage 2 advance, Stage 3 distribution, Stage 4 decline). Only Stage 2 with a proper base is `entry`-worthy.

3. **Base pattern**: Examine weekly OHLCV. Identify the pattern if any (VCP, flat base, cup-with-handle, double-bottom, etc.). Note the base depth and duration. A base shorter than 7 weeks is suspicious.

4. **Volume analysis**: Recent volume relative to 20-day average. Healthy bases show volume drying up during consolidation. Breakouts need volume confirmation (ratio > 1.5).

5. **Risk flags**: Identify any of these conditions:
   - `high_rs_rating`: RS Rating ≥ 95 (extended momentum, late entry risk)
   - `extended_from_ma50`: Price > sma_50 by more than ~10%
   - `low_volume`: Recent volume below 70% of 20-day average for >5 days
   - `thin_base`: Base duration < 7 weeks
   - `earnings_imminent`: (Cannot detect from price data alone — leave to user. Skip this flag for now.)
   - `market_weakness`: Cannot judge from single stock — skip.
   - `sector_overconcentration`: Cannot judge — skip (portfolio context not provided).

6. **Classification decision**: Synthesize the above into `entry / watch / ignore` and assign a confidence (0.00–1.00).

## Output Schema

Return ONLY valid JSON matching this schema. No prose, no markdown, no explanation outside the JSON.

```json
{
  "classification": "entry|watch|ignore",
  "confidence": 0.85,
  "reasoning": "12-week flat base, pivot at 192.50. Price 4.3% below 52w high, RS Rating 89, volume contracting through base — classic Minervini setup. No major risk flags. Entry imminent if breakout with volume confirmation.",
  "pattern": "flat_base|VCP|cup_handle|double_bottom|none",
  "risk_flags": ["high_rs_rating", "extended_from_ma50"]
}
```

## Constraints

- `reasoning`: max 300 characters. Concise, factual, references specific numbers when possible.
- `pattern`: must be one of the listed values. Use `"none"` if no clear pattern is identifiable.
- `risk_flags`: array (possibly empty). Use only the values in §5 above.
- If you cannot make a confident decision (confidence < 0.5), default to `watch` with low confidence and explain why in `reasoning`.

## Forbidden

- Do not output any text outside the JSON.
- Do not invent data not in the input (e.g., do not speculate about earnings dates).
- Do not give entry parameters here — that is a separate task (`calculate_entry_params`).
````

#### 출력 검증

`core/result_parser.py`가 LLM 응답을 받아 다음을 수행:

1. JSON 파싱 (실패 시 1회 재시도, 그래도 실패하면 `llm_calls.error`에 기록 + `daily_analysis`에는 NULL classification으로 저장하지 않고 skip)
2. Pydantic `AnalysisResult` 모델로 검증 (classification 값, confidence 범위, pattern 값, risk_flags 화이트리스트)
3. 검증 실패 시 동일 처리 (skip + error 로그)

### 6.3 (6) `calculate_entry_params()` 프롬프트 설계

#### 호출 조건

`(5)`의 결과가 `classification == "entry"`인 종목에 대해서만 호출.

#### 입력 페이로드

(5)의 입력에 더해 (5)의 결과를 함께 전달:

````
{
  "task": "minervini_entry_params",
  "symbol": "AAPL",
  "market": "NASDAQ",
  "date": "2026-04-25",
  
  "prior_analysis": {
    "classification": "entry",
    "confidence": 0.85,
    "pattern": "flat_base",
    "reasoning": "12-week flat base, pivot at 192.50...",
    "risk_flags": []
  },
  
  // (5)와 동일한 차트·인디케이터 데이터 재포함 (LLM이 다시 봐야 함)
  ...
}
````

#### 프롬프트 본문 (`prompts/calculate_entry_params_v1.md`)

````markdown
You are a Mark Minervini-style position sizer. Given a stock that has been classified as `entry`, compute the proper buy point, stop loss, suggested portfolio weight, volume confirmation requirement, and target zones.

## Inputs

You will receive:
- Identifier (symbol, market, date)
- Prior analysis result (classification, pattern, reasoning, risk flags)
- The same chart and indicator data the prior analysis saw

## Calculation Procedure

1. **Pivot price**: Identify the proper buy point per Minervini rules.
   - For VCP: highest point of the most recent contraction
   - For flat base: high of the base
   - For cup-with-handle: high of the handle
   - Add a small margin (~0.10) to the raw pivot to avoid premature trigger.

2. **Stop loss**: 
   - Default: 7–8% below pivot price
   - If risk flag `extended_from_ma50` present: tighten to 5–6%
   - If pattern is unclear or base is short: tighten to 5%
   - Never wider than 8%.

3. **Suggested weight**:
   - Base case: 20% of total assets (Minervini's typical concentrated position)
   - If risk flag `high_rs_rating` (RS ≥ 95): reduce to 15%
   - If risk flag `thin_base`: reduce to 10%
   - If multiple risk flags: cap at 10%
   - Never exceed 25%.

4. **Volume confirmation**:
   - `required: true`, `ratio_to_ma20: 1.5` for clean breakouts
   - For VCP at very tight contractions: ratio_to_ma20 can be 1.3
   - Always include this requirement.

5. **Expected target**:
   - `conservative`: pivot + base depth (typical first leg)
   - `optimistic`: pivot + 2 × base depth

6. **Valid until**:
   - Default: pivot date + 5 trading days
   - If condition is not met within window, the entry signal expires.
   - Compute as ISO date.

## Output Schema

Return ONLY valid JSON matching this schema:

```json
{
  "pivot_price": 192.50,
  "stop_loss_price": 178.50,
  "stop_loss_pct": -7.27,
  "suggested_weight_pct": 20.0,
  "volume_confirmation": {
    "required": true,
    "ratio_to_ma20": 1.5
  },
  "expected_target": {
    "conservative": 215.00,
    "optimistic": 237.50
  },
  "valid_until": "2026-05-02"
}
```

## Constraints

- `stop_loss_pct`: must be between -8.0 and -5.0.
- `suggested_weight_pct`: must be between 5.0 and 25.0.
- All prices in the same currency as input (no conversion).
- `valid_until`: ISO date string.

## Forbidden

- Do not output text outside the JSON.
- Do not change the classification (this stock is already `entry`).
- Do not invent risk flags not in the prior analysis.
````

#### v1.1 production lock 결과 (Phase 1.3.0 종료, 2026-05-07)

본 §6.3 본문은 **brief 작성 시점(2026-04-26)의 초기 설계안 v0**이다. Phase 1 진행 중 다음 두 차례 주요 변경이 있었다.

**1. v0 → v1 재설계 (Phase 1.2 트랙 B, 2026-05-05, commit `f88bc52`)**

위 본문의 7필드(`pivot_price`, `stop_loss_price`, `stop_loss_pct`, `suggested_weight_pct`, `volume_confirmation`, `expected_target.conservative/optimistic`, `valid_until`)는 1.2 트랙 B B.1 사전 자문 hybrid 적용 단계에서 **13필드로 재설계**됐다.

핵심 차이:
- `volume_confirmation` 객체 → `breakout_volume_requirement` enum 문자열로 단순화 (예: `"ge_1.4x_50day_avg"`)
- `expected_target.conservative/optimistic` 객체 → `expected_target_price` + `expected_target_pct` 단일값으로 단순화 (1차 sell-half 기준만)
- `valid_until` ISO 날짜 → `entry_window_days` int + `max_chase_pct_from_pivot` float로 분리 (시간·가격 차원 분리)
- 신규 추가: `pattern_basis`, `notes`, `known_warnings`, `other_warnings`

**2. v1 → v1.1 minor revision (Phase 1.3.0, 2026-05-07, commit `7a1dd98`)**

NVST B.5.5 1차 Evaluator 평가에서 도출된 (6) 함수 표기·투명성 문제 3건을 v1.1로 minor revision 발행. 13필드 → **16필드** + KnownWarning enum 10 → 12.

| Fix | 항목 | 변경 |
|---|---|---|
| 1 | dual stop_pct 분리 (transparency) | `stop_loss_pct` rename → `stop_loss_pct_from_pivot` + `stop_loss_pct_from_current_price` 신규 둘 다 emit. \|from_current_price\| > 7.5 시 `stop_distance_from_current_price_exceeds_book_limit` known_warning auto-emit |
| 2 | `trigger_price` schema-level 분리 | `pivot_price`(raw) + `trigger_price`(buffered, default `pivot * 1.001`) 둘 다 emit. (5) reasoning과 (6) 구조 필드 간 ambiguity 제거 |
| 3 | breakout volume mismatch auto-warning | `observed_breakout_volume_ratio` 신규 (LLM이 chart에서 자동 추출). observed < requirement threshold(1.3/1.4/1.5) 시 `breakout_volume_below_requirement` known_warning auto-emit (size 조정과 무관) |

**스키마 신규 4필드**: `current_price` (분석 시점 종가 echo), `trigger_price` (buffered), `stop_loss_pct_from_current_price`, `observed_breakout_volume_ratio`.

**v1.1 검증 결과**:
- 단위 테스트 53/53 통과 (test_entry_params 53건, v1.1 신규 14건)
- NVST 합성 검증 6/6 OK (auto-emit 2종 모두 정상 trigger)
- v1.1 LLM 호출 메타: model=claude-sonnet-4-5, duration 107.9s, prompt 31,498 tokens, completion 5,492 tokens

**3. stop_loss_pct 범위 [-8, -5] → [-10, -5] 확장** (v1 시점 변경)

위 본문 Constraints의 `must be between -8.0 and -5.0`은 **사전 자문 §0.6 채택으로 [-10.0, -5.0]으로 확장**됐다. 사유:
- 책 절대 한도(O'Neil 7-8%, Minervini 10% "uncle point")의 더 보수적인 한도까지 허용
- 단, 일반적으로는 5~8% 범위 내가 권장. -8 ~ -10은 risk_flag 기반 logical stop이 handle low 등 구조적 위치에 자연 도달할 때만 사용
- v1.1에서는 `stop_loss_pct_from_pivot`에 동일 제약 유지

**4. v1.1 production lock 시점 SSoT**

코드의 실제 SSoT는 다음:
- 프롬프트 v1.1: `apps/llm-analysis/prompts/calculate_entry_params_v1_1.md` (v1 보존됨)
- Pydantic 모델: `apps/llm-analysis/models/entry_params.py` (v1.1 auto-emit validator 포함)
- Result parser: `apps/llm-analysis/core/result_parser.py` (v1 → v1.1 legacy 매핑)
- Settings: `apps/llm-analysis/config/settings.yaml`의 `prompts.calculate_entry_params: v1_1`
- 스키마 정의: `_meta/05_GLOSSARY.md` Part B.2 entry_params (v1.1 production lock 본문)

**5. v0 본문 보존 정책**

위 §6.3 v0 본문은 **brief의 시간적 SSoT 보존을 위해 그대로 둔다** (ADR-014 §1 (a) Implementation Detail 정밀화 카테고리 — 구현 정밀화 이력 보존). 브리프 본문 v0과 코드 v1.1의 차이는 본 "v1.1 production lock 결과" 섹션이 명시한 5가지 항목으로 구성된다.

### 6.4 프롬프트 버저닝

- 본 brief 시점의 프롬프트는 `v1`
- 프롬프트 변경 시 새 파일(`analyze_chart_v2.md`) + `settings.yaml`의 `prompts.analyze_chart`를 `"v2"`로 갱신
- `llm_calls.request_payload`에 어느 버전 프롬프트가 사용됐는지 메타데이터로 함께 기록 (예: payload 안에 `"prompt_version": "v1"` 필드 추가)
- 버전 변경은 ADR로 기록 (예: ADR-011 "(5) 프롬프트 v2 도입")

### 6.5 프롬프트 튜닝의 위치

ROADMAP에 명시된 대로 **프롬프트 튜닝은 Phase 1의 가장 큰 시간 소요**. brief의 §3 단계별 작업의 1.1 단계가 사실상 프롬프트 튜닝 단계.

튜닝 절차:
1. 1~2개 종목으로 수동 호출 (`run_single_symbol.py`)
2. 응답 검토 → 프롬프트 수정 → 재호출
3. 합리적 응답 안정화 후 5~10개 종목 배치
4. 결과 검토 → 프롬프트 미세 조정
5. 50~100개 풀 배치 시도
6. v1 확정

각 미세조정마다 **프롬프트 파일을 새 버전으로 만들 필요는 없음** (튜닝 중에는 같은 v1 파일을 수정). v1 확정 후 commit. 차후 큰 변경만 v2.

---

## §3. 단계별 작업

ADR-011 결정에 따라 Phase 1을 세 단계로 쪼갠다. 각 단계 종료 시 사용자가 결과를 검토하고 진행 여부를 결정한다 (헌법 §3.3).

### 3.1 단계 1.1 — DB 마이그레이션 + (5) 분석 함수 구현 + 백엔드 추상화 검증

**목표**: 단일 종목 1개에 대해 (5) `analyze_chart`가 정상 동작하고, `daily_analysis_kr/us`·`llm_calls`에 결과가 기록되며, 백엔드 추상화(`LLMBackend`)가 CLI/API 양쪽으로 작동함을 입증.

**작업 항목**:

| # | 작업 | 산출물 |
|---|---|---|
| 1.1.1 | DB 마이그레이션 3종 산출물 작성 | Alembic 파일 + raw SQL 파일 + 운영 큐 Q-002 |
| 1.1.2 | 운영 환경에 마이그레이션 적용 (사용자 직접) | Q-002 완료 처리 |
| 1.1.3 | `apps/llm-analysis/` 디렉토리 골격 생성 | README, settings.yaml, requirements.txt 등 §5 구조 |
| 1.1.4 | `LLMBackend` 추상화 인터페이스 정의 | `core/anthropic_client.py` |
| 1.1.5 | CLI 백엔드 구현 (`ClaudeCodeCLIBackend`) | subprocess 호출 + stdout/stderr 캡처 + 토큰 추정 |
| 1.1.6 | API 백엔드 구현 (`AnthropicAPIBackend`) | `anthropic` Python SDK 호출 (검증 목적, 즉시 사용 안 함) |
| 1.1.7 | `llm_calls` 기록 wrapper | 모든 호출이 자동 기록되도록 데코레이터 또는 with 컨텍스트 |
| 1.1.8 | (5) 프롬프트 v1 작성 | `prompts/analyze_chart_v1.md` |
| 1.1.9 | `data_loader.py` 구현 | DB에서 입력 페이로드 구성 (일봉 60일, 주봉 52주, 인디케이터, conditions_met 등) |
| 1.1.10 | `prompt_builder.py` 구현 | 페이로드 → CLI/API 입력 형식으로 직렬화 |
| 1.1.11 | `result_parser.py` + Pydantic `AnalysisResult` 모델 | 파싱 실패 처리 + 재시도 1회 |
| 1.1.12 | `run_single_symbol.py` CLI 작성 | 단일 종목 디버깅용 진입점 |
| 1.1.13 | 단일 종목 호출 검증 (CLI 백엔드) | 표본 5종목으로 호출, JSON 응답 받기, DB에 기록 |
| 1.1.14 | 단일 종목 호출 검증 (API 백엔드, 1회만) | 추상화가 작동함을 입증. 같은 종목으로 호출 후 응답 비교 |
| 1.1.15 | 프롬프트 튜닝 (5~10회 반복) | 응답 안정성 확보, v1 확정 |

**완료 기준**:
- 표본 종목에 대해 CLI 백엔드 호출이 안정적 (실패율 < 10%)
- 응답이 `AnalysisResult` 스키마를 만족 (classification, confidence, reasoning, pattern, risk_flags)
- `llm_calls` 테이블에 호출 메타데이터 기록됨 (cost_usd는 CLI 모드에서 NULL OK)
- `daily_analysis_kr` 또는 `daily_analysis_us`에 결과 행 생성됨
- 같은 종목을 CLI와 API 양쪽으로 호출했을 때 호출자 코드는 동일 (`backend` 설정만 변경)

**소요 추정**: 5~7일 (대부분 프롬프트 튜닝)

**1.1 종료 시 사용자 결정 포인트**:
- 응답 품질이 만족스러우면 → 1.2로
- 프롬프트가 더 다듬어져야 하면 → 1.1 연장
- 백엔드 추상화에 문제가 있으면 → ADR-011 §6 절차로 재설계

---

### 3.2 단계 1.2 — (6) 진입 파라미터 함수 + 정량 검증

**목표**: (5)에서 `entry`로 분류된 종목에 대해 (6) `calculate_entry_params`가 정상 동작하고, 산출된 파라미터(피봇 가격·손절·비중)가 미너비니 원칙에 부합함을 사용자가 검증.

**전제**: 1.1 완료. (5)의 출력 형식이 안정.

**작업 항목**:

| # | 작업 | 산출물 |
|---|---|---|
| 1.2.1 | (6) 프롬프트 v1 작성 | `prompts/calculate_entry_params_v1.md` |
| 1.2.2 | `EntryParams` Pydantic 모델 + 검증 로직 | stop_loss_pct ∈ [-10, -5] (사전 자문 §0.6 채택, 본 문서 작성 시 [-8, -5]에서 확장), suggested_weight_pct ∈ [0, 25] 등 |
| 1.2.3 | `result_parser.py`에 (6) 응답 파싱 추가 | 동일 패턴 |
| 1.2.4 | `run_single_symbol.py`에 `--with-entry-params` 옵션 추가 | (5) 후 (6) 자동 호출 |
| 1.2.5 | 표본 entry 종목에 (6) 호출 (5~10건) | 실제 entry 분류된 종목으로 검증 |
| 1.2.6 | 산출 파라미터 합리성 검토 (사용자) | 피봇 가격이 차트 상 합리적인지, 손절선이 7~8% 룰을 따르는지 |
| 1.2.7 | (6) 프롬프트 튜닝 (5~10회 반복) | 안정화 후 v1 확정 |
| 1.2.8 | `daily_analysis_kr/us.entry_params` 컬럼 채움 검증 | JSON 스키마 일치 |

**완료 기준**:
- entry 분류된 표본 종목 모두에 대해 (6)이 정상 응답
- `entry_params` JSON이 GLOSSARY Part B.2 스키마 일치
- 사용자가 산출 파라미터를 정성적으로 합리적이라 판단

**소요 추정**: 3~5일

**1.2 종료 시 사용자 결정 포인트**:
- 진입 파라미터가 신뢰할 만하면 → 1.3으로
- 미세 조정 필요하면 → 1.2 연장 또는 (6) 프롬프트 v2

---

### 3.3 단계 1.3 — 일일 배치 진입점 + 7거래일 운영 검증

**목표**: 사용자가 명시적으로 트리거하면, 그날의 미너비니 통과 종목 전체에 대해 (5)→(6)이 자동 실행되고 결과가 누적된다. **7거래일 누적 결과로 Phase 1 종료 조건을 평가한다.**

**작업 항목**:

| # | 작업 | 산출물 |
|---|---|---|
| 1.3.1 | `run_daily_analysis.py` 메인 진입점 작성 | KR/US 분리 처리, 일일 상한, 캐싱, dry-run 지원 |
| 1.3.2 | 일일 상한 로직 구현 (`cost_tracker.py`) | settings.yaml의 `daily_call_limits` 적용 |
| 1.3.3 | 캐싱 로직 (`skip_if_exists`) | 같은 (symbol, date)에 결과 있으면 스킵 |
| 1.3.4 | CLI 인자 처리 (`--region`, `--date`, `--limit`, `--force-recompute`, `--dry-run`) | argparse로 깔끔히 |
| 1.3.5 | 에러·재시도 처리 | API/CLI 호출 실패 시 settings.yaml의 `retry` 정책에 따라 |
| 1.3.6 | `show_cost_summary.py` 작성 | 일/주/월 호출 수·비용(API 모드) 보고 |
| 1.3.7 | 사용자 트리거 방식 결정 + 문서화 | 옵션: PowerShell 수동 실행 / Windows Task Scheduler 매일 한 번 사용자 PC 깨어있을 때 / 향후 대시보드 버튼 (Phase 3) |
| 1.3.8 | 운영 환경 적용 (Q-003 또는 후속 큐 항목) | git pull + 첫 수동 실행 |
| 1.3.9 | 7거래일 누적 데이터 수집 | 매일 사용자가 트리거, 결과 누적 |
| 1.3.10 | 누적 결과 검토 (사용자) | classification 분포, confidence 분포, entry 종목의 사용자 판단과의 일치도 |
| 1.3.11 | Phase 1 종료 조건 §1.2 평가 | "쓸만하다" 판단 |

**완료 기준 (Phase 1 종료 조건)**:
- 7거래일 누적 데이터 존재
- KR + US 합쳐 최소 50개 이상의 분석 행 누적 (정성 평가에 충분한 표본)
- 사용자가 결과 품질을 정성적으로 만족 ("쓸만하다")
- 헌법 위배 없음 (Auditor 세션에서 확인)
- 운영 큐 항목 모두 "완료" 섹션으로 이동

**소요 추정**: 1.3.1~1.3.8 작업 4~5일 + 1.3.9 7거래일 운영 + 1.3.10~11 검토 1~2일 = **약 2주**

#### 1.3 실제 운영 결과 (Phase 1 종료 후 본문 통합, 2026-05-09)

**실제 진행 기간**: 2026-05-06 ~ 2026-05-08 (약 3일, 추정 2주의 0.2배 — 7거래일 누적 운영을 백필 + 자연 운영 혼합 방식으로 단축)

**백필 + 자연 운영 혼합 방식 채택**:

원래 계획(매일 사용자 트리거 7거래일 = 7일 소요)을 다음 혼합 방식으로 압축:

- **1.3.9-A 백필** (2026-05-07): KR(4/23~5/4 7거래일) + US(4/24~5/4 7거래일) → 141행 + 158회 LLM 호출. 사용자가 한 번에 강제 트리거하여 누적 데이터 확보.
- **1.3.9-B 자연 운영** (2026-05-06 US): Q-003 PROD 적용 후 첫 자동 트리거 → 26행. Task Scheduler 정상 작동 검증.
- **합계**: 167행 (KR 70 + US 97), §9.1 게이트 8번 기준(50행 이상)의 3.3배.

**채택 사유**:
- 백필만 사용 시 자동 트리거 환경(ADR-012) 검증 불가
- 자연 운영만 사용 시 7거래일 자연 누적까지 7일 소요 + entry 발생 변동성 큼
- 혼합으로 "데이터 체적 충분 + 자동 운영 검증 동시 달성"

**한계**: §9.2 기준 1 (entry 10개 70%+ 표본)의 정식 충족은 entry 자연 발생률(B.5.5 기준 0.25%)과 167행 표본 크기 정합으로 entry 0건 → 운용적 완화 처리 (대체 평가 7건 100% 합리, Evaluator 객관 검증). Phase 2에서 자연 누적 entry-side 평가 sprint 별도 진행.

**커밋 트레일**:
- 1.3.0 (v1.1 fix): `7a1dd98`
- 1.3.1~1.3.8 (메인 진입점·모니터링·Q-003 등록): `39992ff`
- 1.3.9 (PROD 적용 + Windows fix + 백필): `d5f359d`, merge `ccdc54e`
- 1.3.10~11 (정성 평가 + 종료 보고): `phase1/1.3-daily-analysis` 브랜치 HEAD

---

### 3.4 단계 간 게이트

각 단계 종료 시 다음을 수행:

1. Builder가 `_meta/phases/phase1_progress.md`에 단계 종료 보고 작성 (간단히)
2. 사용자가 검토하고 다음 단계 진행 여부 결정
3. 진행 결정 시 다음 단계 시작 (Builder 세션 재개)
4. 보류 또는 재작업 시 추가 ADR 또는 brief 갱신

이 게이트는 ROADMAP의 Phase 종료 감사보다 가벼움. 그러나 단계별로 점검 대화를 거치는 게 안전.

---

## §7. 비용·상한·에러·재시도 정책

ADR-011 결정에 따라 본 Phase는 CLI 백엔드 기본. 비용 메트릭 정책이 백엔드별로 다름.

### 7.1 비용 추적

#### CLI 모드 (Phase 1 기본)
- `llm_calls.cost_usd` = NULL (Max 플랜 정액제)
- 대신 `llm_calls.prompt_tokens`, `completion_tokens`는 **추정값**으로 채움
  - 추정 방법: `tiktoken` 라이브러리 또는 `len(text) / 4` 근사치
  - 추정값임을 `request_payload` JSON 안에 메타로 표시:
```json
    {"prompt_text": "...", "_meta": {"tokens_estimated": true}}
```
- 비용 보고는 호출 횟수와 추정 토큰 수만 (실 비용은 Max 플랜 청구서로 확인)

#### API 모드 (전환 시점부터)
- `cost_usd` = API 응답의 정확한 토큰 × 모델 단가
- 모델 단가는 `settings.yaml`에 정의 (가격 변경 시 갱신)

```yaml
anthropic:
  pricing:
    claude-sonnet-4-5:
      input_per_1m_tokens: 3.0
      output_per_1m_tokens: 15.0
    claude-haiku-4-5:
      input_per_1m_tokens: 0.80
      output_per_1m_tokens: 4.0
```

### 7.2 일일 호출 상한 (점검 3 결정)

#### 기본값
```yaml
daily_call_limits:
  enabled: true
  kr: 50
  us: 50
  hard_stop_on_exceed: true
```

#### 동작
- 매 호출 직전에 그날 누적 호출 수 확인 (`SELECT COUNT(*) FROM llm_calls WHERE timestamp >= today AND module LIKE 'analysis_%_kr'`)
- 한도 도달 시:
  - `hard_stop_on_exceed: true` → 즉시 중단, 나머지 종목 스킵, sync_log에 경고 기록
  - `hard_stop_on_exceed: false` → 경고만 로그, 계속 진행

#### CLI override
- `--limit 30` 인자로 즉시 변경 가능
- `--limit 0` → 그 region 분석 스킵 (안전 차단)

#### ADR-012 자동 트리거 환경에서의 강제 사항

ADR-012 §3.1에 따라 본 Phase의 자동 트리거 환경(Task Scheduler)에서는 다음을 **강제**한다:

- `daily_call_limits.enabled: true` — 끄면 안 됨
- `hard_stop_on_exceed: true` — 한도 도달 시 반드시 즉시 중단
- KR/US 각 50건 권장 (사용자 운영 경험에 따라 조정 가능, 단 무한대로 풀지 말 것)

이유: 자동 트리거 환경에서 한도 초과는 약관 위반 징후일 가능성이 높다. 코드 버그(무한루프, 중복 호출)도 같은 신호로 잡힘. hard stop이 약관 보호의 가장 직접적 안전장치.

수동 트리거(보조용 PowerShell 실행) 시에도 같은 설정을 그대로 사용하지만, `--limit` CLI override로 임시 조정 가능 (디버깅·force-recompute 등).

### 7.3 캐싱 정책

```yaml
caching:
  skip_if_exists: true
```

#### 동작
- (5) 호출 직전 `daily_analysis_{kr,us}` 조회. 해당 (symbol, date) 행 존재하면:
  - `skip_if_exists: true` → 스킵 (재호출 안 함)
  - `skip_if_exists: false` → 덮어쓰기

#### `--force-recompute` CLI 인자
- 캐싱 무시하고 강제 재호출
- 프롬프트 튜닝 후 재계산할 때 사용

### 7.4 비용 알림

```yaml
cost_alerts:
  daily_threshold_usd: 5.00
  monthly_threshold_usd: 60.00
```

#### CLI 모드
- 추정 비용으로 알림 트리거 (정확하지 않지만 폭주 감지용)
- 추정 비용은 `prompt_tokens × 추정 단가` (Sonnet 4.5 단가로 가정)

#### API 모드
- 정확한 누적 cost_usd로 알림 트리거

#### 알림 방식
- Phase 1에서는 `sync_log` 테이블에 `WARN` 상태로 기록
- Phase 2 이메일 발송 도입 후 메일 알림 추가 (별도 brief)

### 7.5 에러 처리

#### 호출 실패 분류

| 에러 유형 | 처리 |
|---|---|
| 네트워크 오류 / 타임아웃 | 재시도 (settings.yaml의 retry 정책) |
| API 한도 초과 (429) | 백오프 후 재시도, 3회 실패 시 중단 |
| Max 플랜 5시간 윈도우 한도 초과 (CLI) | 현재 세션 즉시 중단, 다음 윈도우까지 대기 안내 메시지 |
| 응답 파싱 실패 (JSON invalid) | 1회 재시도. 재시도도 실패 시 해당 종목 스킵 + `llm_calls.error` 기록 |
| 응답 스키마 불일치 (Pydantic) | 1회 재시도. 동일 처리 |
| LLM 자체 거부 (안전 필터 등) | 즉시 스킵 + 로그 |

#### 재시도 정책 (`settings.yaml`)

```yaml
anthropic:
  retry:
    max_attempts: 3
    backoff_base_sec: 2
    backoff_max_sec: 30
```

지수 백오프: 2s, 4s, 8s. max 30s.

### 7.6 부분 실패 허용

배치 실행 중 일부 종목 실패는 전체 중단 사유 아님. 끝까지 진행하고 마지막에 실패 요약 보고:

```
[run_daily_analysis] KR 분석 완료
  성공: 47/50
  실패: 3
    005930: parse_error (재시도 후 실패)
    373220: api_timeout (3회 재시도 후 실패)
    005380: schema_violation
  총 소요: 18분 32초
```

이 요약은 sync_log에 기록되고, 사용자가 다음날 검토.

### 7.7 킬 스위치

```yaml
modules:
  analyze_chart: true
  calculate_entry_params: true
```

- 둘 중 하나를 `false`로 설정하면 해당 모듈 호출 안 함
- `analyze_chart: false` → 전체 분석 중단 (비상시)
- `calculate_entry_params: false` → (5)만 돌고 (6) 스킵 (튜닝 중 유용)

CLI override: `--disable-entry-params`, `--disable-analyze` (긴급 차단)

---

## §8. 배치 통합 방식

ADR-012에 따라 본 Phase는 **Windows Task Scheduler를 통한 자동 트리거**를 채택한다. ADR-011 §1의 "사용자 명시적 트리거" 원칙은 ADR-012에 의해 §1만 부분 개정되어 자동 트리거를 허용한다.

본 §8은 운영 환경(Windows + PowerShell)에서 어떻게 자동 트리거를 구성하고, 그 위에 안전장치를 어떻게 얹을지 정의한다.

### 8.1 트리거 방식 비교 (ADR-012 결정 반영)

| 방식 | 설명 | 사용자 의도 개입 | 약관 위험 | Phase 1 채택 |
|---|---|---|---|---|
| **A. 수동 PowerShell 실행** | 사용자가 운영 PC에서 직접 명령어 실행 | ✅ 매번 | 낮음 | 보조 (디버깅·예외 시) |
| **B. 사용자 직접 실행 + 즉시 메일 (Phase 2)** | A와 동일, 결과를 메일로 받음 | ✅ 매번 | 낮음 | Phase 2 |
| **C. Windows Task Scheduler 자동 실행** | 정해진 시각에 자동 실행 | ✅ 등록 시점 (1회) + 매일 동일 의도 반복 | 중간 (회색, ADR-012 §3 모니터링으로 보완) | ✅ **기본 (ADR-012)** |
| **D. 대시보드 "분석 실행" 버튼** | 웹 UI에서 사용자가 클릭 | ✅ 매번 | 낮음 | Phase 3 |
| **E. 모바일 앱 "분석 실행"** | 앱에서 사용자가 클릭 | ✅ 매번 | 낮음 | Phase 3 이후 |

**Phase 1 결정 (ADR-012)**:
- **기본 트리거 = C (Windows Task Scheduler 자동 실행)**
- A는 보조 — 디버깅, 단일 종목 재호출, force-recompute, 자동 트리거 일시 중단 후 임시 운영 시 사용
- D/E는 Phase 3에서 도입 — 같은 백엔드(`run_daily_analysis.py`)를 호출하므로 자연스럽게 연결

### 8.2 자동 트리거 시각

ADR-012 §2에 따라 다음 시각을 권장 기본값으로 등록한다.

| Region | 트리거 시각 (KST) | 산정 근거 |
|---|---|---|
| **US** | **16:00** | US daily 08:00 시작, 최대 14:00 종료 + 미너비니 ~14:10 + ~1h50m 안전 마진 (정시 보정) |
| **KR** | **21:00** | KR daily 19:00 시작, 최대 19:30 종료 + 미너비니 ~19:40 + ~1h20m 안전 마진 (정시 보정) |

**SSoT 정책 (ADR-012 §2)**:
- 실제 트리거 시각의 SSoT는 **Windows Task Scheduler에 등록된 값**이다.
- `apps/llm-analysis/config/settings.yaml`의 `analysis_trigger` 섹션은 운영 의도를 사람이 추적하기 위한 문서이며, 코드 동작에는 영향을 주지 않는다.
- 시각 변경 시 ① Task Scheduler 등록 갱신 ② settings.yaml 갱신 ③ 큰 변경이면 ADR 후속 — 세 가지를 함께 수행. 절차는 운영 큐 항목으로 등록.

### 8.3 운영 환경 자동 트리거 등록 절차

#### 8.3.1 PowerShell 래퍼 스크립트 (자동·수동 공통 진입점)

`apps/llm-analysis/ops/scheduler/windows/run_analysis_today.ps1`

```powershell
# 매일 자동 실행되거나 사용자가 수동으로 실행하는 분석 트리거
# Usage:
#   .\run_analysis_today.ps1                  # 그날 region 모두 (KR + US)
#   .\run_analysis_today.ps1 -Region KR       # 한 region만
#   .\run_analysis_today.ps1 -DryRun          # 호출 안 하고 대상만 확인
#   .\run_analysis_today.ps1 -ForceRecompute  # 캐시 무시 재계산

param(
    [string]$Region = "BOTH",     # "KR" | "US" | "BOTH"
    [switch]$DryRun,
    [switch]$ForceRecompute
)

$today = Get-Date -Format "yyyy-MM-dd"
$projectRoot = "C:\path\to\DataBatcher"   # 운영 환경에서 실제 경로로 치환

cd $projectRoot

$flags = @()
if ($DryRun) { $flags += "--dry-run" }
if ($ForceRecompute) { $flags += "--force-recompute" }

if ($Region -eq "KR" -or $Region -eq "BOTH") {
    Write-Host "=== KR 분석 시작 ($today) ===" -ForegroundColor Green
    python apps\llm-analysis\scripts\run_daily_analysis.py --region KR --date $today @flags
}

if ($Region -eq "US" -or $Region -eq "BOTH") {
    Write-Host "=== US 분석 시작 ($today) ===" -ForegroundColor Green
    python apps\llm-analysis\scripts\run_daily_analysis.py --region US --date $today @flags
}

Write-Host "=== 결과 요약 ===" -ForegroundColor Cyan
python apps\llm-analysis\scripts\show_cost_summary.py --period today
```

#### 8.3.2 Task Scheduler 등록 스크립트

`apps/llm-analysis/ops/scheduler/windows/install_task.ps1`

```powershell
# Task Scheduler에 KR/US 분석 작업을 등록한다.
# 운영 큐 Q-003에서 사용자가 한 번 실행.

param(
    [string]$ProjectRoot = "C:\path\to\DataBatcher"   # 실제 경로로 치환
)

$scriptPath = Join-Path $ProjectRoot "apps\llm-analysis\ops\scheduler\windows\run_analysis_today.ps1"

# US 분석 — 매일 16:00 KST
$usAction = New-ScheduledTaskAction -Execute "PowerShell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`" -Region US"
$usTrigger = New-ScheduledTaskTrigger -Daily -At 16:00
$usSettings = New-ScheduledTaskSettingsSet -StartWhenAvailable `
    -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 2)

Register-ScheduledTask -TaskName "LLMAnalysis_US" `
    -Action $usAction -Trigger $usTrigger -Settings $usSettings `
    -Description "Phase 1 LLM analysis for US region (ADR-012, recommended 16:00 KST)"

# KR 분석 — 매일 21:00 KST
$krAction = New-ScheduledTaskAction -Execute "PowerShell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`" -Region KR"
$krTrigger = New-ScheduledTaskTrigger -Daily -At 21:00
$krSettings = New-ScheduledTaskSettingsSet -StartWhenAvailable `
    -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 2)

Register-ScheduledTask -TaskName "LLMAnalysis_KR" `
    -Action $krAction -Trigger $krTrigger -Settings $krSettings `
    -Description "Phase 1 LLM analysis for KR region (ADR-012, recommended 21:00 KST)"

Write-Host "=== Task Scheduler 등록 완료 ===" -ForegroundColor Green
Get-ScheduledTask -TaskName "LLMAnalysis_*" | Format-Table TaskName, State, @{Name="NextRun"; Expression={(Get-ScheduledTaskInfo $_).NextRunTime}}
```

#### 8.3.3 일시 중단·재개·삭제 명령

운영 중 통제권 행사를 위한 표준 명령어 (ADR-012 §5 메커니즘 1):

```powershell
# 일시 중단 (작업 disable)
Disable-ScheduledTask -TaskName "LLMAnalysis_US"
Disable-ScheduledTask -TaskName "LLMAnalysis_KR"

# 재개 (작업 enable)
Enable-ScheduledTask -TaskName "LLMAnalysis_US"
Enable-ScheduledTask -TaskName "LLMAnalysis_KR"

# 완전 삭제
Unregister-ScheduledTask -TaskName "LLMAnalysis_US" -Confirm:$false
Unregister-ScheduledTask -TaskName "LLMAnalysis_KR" -Confirm:$false

# 상태 확인
Get-ScheduledTask -TaskName "LLMAnalysis_*"
Get-ScheduledTaskInfo -TaskName "LLMAnalysis_US"   # LastRunResult, NextRunTime 등
```

### 8.4 모니터링·안전장치 (ADR-012 §3)

자동 트리거를 허용하는 대가로 다음 4종 안전장치를 모두 가동한다. Builder는 1.1~1.3 단계에서 누락 없이 구현한다.

#### 8.4.1 일일 호출 상한 (강제, hard stop)

`settings.yaml`:

```yaml
daily_call_limits:
  enabled: true              # 자동 트리거 환경에서 반드시 true
  kr: 50
  us: 50
  hard_stop_on_exceed: true  # 자동 트리거 환경에서 반드시 true
```

구현 위치: `core/cost_tracker.py`의 `check_daily_limit(region, module)` 함수
- 매 (5)/(6) 호출 직전 호출됨
- 한도 도달 시 `DailyCallLimitExceeded` 예외 raise
- `run_daily_analysis.py`가 이 예외를 catch해서 sync_log에 WARN 기록 + 즉시 종료 (return 0, 나머지 종목 스킵)

#### 8.4.2 sync_log 이상 기록

다음 이벤트는 모두 `sync_log` 테이블에 기록:

| 이벤트 | sync_log 상태 | 기록 시점 |
|---|---|---|
| 일일 호출 상한 초과 | `WARN` | 한도 도달 직후 |
| 비용 알림 임계값 초과 | `WARN` | 일일 누적 추정 비용이 임계값 넘은 직후 |
| 호출 실패율 30% 이상 | `WARN` | 한 region 분석 종료 시점에 집계 |
| Max 플랜 5시간 윈도우 한도 초과 | `WARN` | CLI 백엔드의 stderr 패턴 매칭 |
| 응답 파싱 실패율 20% 이상 | `WARN` | 한 region 분석 종료 시점에 집계 |
| Task Scheduler 작업 실행 실패 | `ERROR` | 별도 점검 (Get-ScheduledTaskInfo) |

구현 위치: `core/anthropic_client.py`의 호출 wrapper + `run_daily_analysis.py`의 종료 부분

#### 8.4.3 약관 위반 징후 감지 — 자동 차단

`core/cost_tracker.py`에 주간 카운터:

```python
def check_terms_violation_signals() -> bool:
    """
    Max 플랜 한도 초과가 한 주 안에 3회 이상이면 True.
    True 반환 시 자동 트리거를 비활성화하고 사용자 알림 (sync_log ERROR).
    """
```

- 매 region 분석 시작 직전 호출
- True 반환 시:
  1. 분석을 시작하지 않고 즉시 종료
  2. sync_log에 ERROR 기록 (사용자 점검 필요)
  3. ADR-012 §4 절차로 API 백엔드 전환 검토 알림

자동 차단은 위 한 가지 조건만. 다른 징후(Anthropic 계정 통보, 정책 변경 등)는 사용자가 인지해서 수동 대응.

#### 8.4.4 호출 로그 주간 점검

사용자가 주간 1회 실행:

```powershell
# apps/llm-analysis/scripts/show_cost_summary.py --period week
# 또는 직접 SQL:
docker exec -i mysql-standalone-mysql mysql -u root -p"$env:MYSQL_ROOT_PASSWORD" trade -e "
SELECT DATE(timestamp) AS d,
       module,
       COUNT(*) AS calls,
       SUM(CASE WHEN error IS NOT NULL THEN 1 ELSE 0 END) AS errors,
       ROUND(AVG(duration_ms)/1000, 1) AS avg_sec
FROM llm_calls
WHERE timestamp >= DATE_SUB(NOW(), INTERVAL 7 DAY)
GROUP BY d, module
ORDER BY d DESC, module;
"
```

결과를 `phase1_progress.md`의 "주간 운영 메모" 섹션에 첨부 (Builder 또는 사용자가 작성).

### 8.5 통제권 메커니즘 (ADR-012 §5)

자동 트리거 운영 중 사용자가 통제권을 행사할 수 있는 4가지 메커니즘:

| # | 메커니즘 | 적용 시나리오 | 명령 |
|---|---|---|---|
| 1 | Task Scheduler disable | 자동 실행 자체를 임시 중단 | `Disable-ScheduledTask -TaskName "LLMAnalysis_*"` |
| 2 | settings.yaml 킬 스위치 | 작업은 실행되되 LLM 호출 차단 | `modules.analyze_chart: false` |
| 3 | 부분 비활성화 | (5)만 운영, (6)은 차단 | `modules.calculate_entry_params: false` |
| 4 | 매매 게이트 부재 | LLM 결과가 자동 매매로 이어지지 않음 (구조적) | 코드상 경로 자체가 없음 (Phase 6까지) |

메커니즘 1은 GUI(Windows 작업 스케줄러)에서도 동일 기능. 우클릭 → "사용 안 함".

### 8.6 사용자 경험 흐름 (Phase 1 종료 시)

```
[새벽~오전] daily cron 자동 실행 (기존 흐름)
  → kr_daily_update (19:00 시작), us_daily_update (08:00 시작)
  → 각 region rs_update, minervini_update
  → minervini_screen_results_kr/us 신규 데이터 적재 (conditions_met 채워짐)

[오후 16:00 KST] Task Scheduler "LLMAnalysis_US" 자동 실행
  → run_analysis_today.ps1 -Region US
  → 약 5~30분 소요 후 daily_analysis_us에 결과 누적
  → llm_calls에 호출 로그 기록

[저녁 21:00 KST] Task Scheduler "LLMAnalysis_KR" 자동 실행
  → run_analysis_today.ps1 -Region KR
  → 약 5~30분 소요 후 daily_analysis_kr에 결과 누적
  → llm_calls에 호출 로그 기록

[사용자 검토 시점 — 본인 일정에 맞춰]
  → mysql 또는 향후 대시보드(Phase 3)로 daily_analysis_kr/us 조회
  → entry/watch/ignore 분류와 reasoning 검토
  → "쓸만하다" 판단 (Phase 1 종료 조건 §1.2)

[주간 1회 — 사용자 정한 시점]
  → show_cost_summary.py --period week 또는 §8.4.4 쿼리
  → llm_calls 패턴 점검 + sync_log WARN/ERROR 점검
  → phase1_progress.md "주간 운영 메모" 섹션 갱신
```

Phase 1에서는 검토 단계가 mysql 직접 쿼리. Phase 3에서 대시보드 카드로 발전.

### 8.7 운영 큐 항목 (Q-003)

본 Phase 1.3 단계에서 운영 환경에 적용해야 할 사항:

```markdown
### Q-003: Phase 1 LLM 분석 모듈 운영 환경 적용 (Phase 1 1.3 완료 시 정식 등록)

**관련 commit**: phase1/* 브랜치 머지 commit
**관련 ADR**: ADR-009, ADR-011, ADR-012
**위험도**: 중간 (코드 변경 + Task Scheduler 등록)
**예상 소요**: 30분

**해야 할 작업**:
1. git pull (운영 PC)
2. apps/llm-analysis/ 의존성 설치 (`pip install -r apps/llm-analysis/requirements.txt`)
3. apps/llm-analysis/.env 설정
   - CLI 백엔드: Max 플랜 로그인 상태 확인
   - API 백엔드 (전환 시): ANTHROPIC_API_KEY 셋업
4. config/settings.yaml 검토 + 운영 환경에 맞게 조정
   - daily_call_limits.enabled: true (필수, ADR-012 §3.1)
   - hard_stop_on_exceed: true (필수, ADR-012 §3.1)
   - analysis_trigger.kr.recommended_time_kst: "21:00"
   - analysis_trigger.us.recommended_time_kst: "16:00"
5. ops/scheduler/windows/run_analysis_today.ps1 첫 실행 (--dry-run)
6. ops/scheduler/windows/run_analysis_today.ps1 첫 실제 실행 (수동, 1종목 또는 소규모)
7. 정상 동작 확인 후 install_task.ps1 실행 → Task Scheduler에 KR/US 등록
8. Get-ScheduledTask로 등록 확인
9. 다음 자동 트리거 시각(US 16:00 또는 KR 21:00)에 실제 실행되는지 관찰

**완료 기준**:
- LLMAnalysis_US, LLMAnalysis_KR 두 작업이 Task Scheduler에 등록됨
- 첫 자동 실행이 정상 종료됨 (Get-ScheduledTaskInfo의 LastRunResult = 0)
- daily_analysis_kr/us에 결과 행 생성됨
- llm_calls에 호출 로그 남음
- sync_log에 WARN/ERROR 없음 (또는 알려진 이상만)
```

이 항목은 Phase 1 1.3 완료 시점에 정식 등록 + Phase 1.3 게이트(§9.1) 통과 후 사용자가 실제 적용.

---

## §9. 검증·승인 기준

### 9.1 단계별 게이트 체크리스트

각 단계 종료 시 사용자가 확인.

#### 1.1 게이트 (DB + (5) + 추상화)

- [ ] `daily_analysis_kr`, `daily_analysis_us`, `llm_calls` 테이블이 개발 환경에 존재
- [ ] Q-002 운영 큐 항목이 등록됨 (운영 환경 적용은 1.3 단계로 미뤄도 됨)
- [ ] `apps/llm-analysis/` 디렉토리 구조가 §5.2와 일치
- [ ] `LLMBackend` 인터페이스가 정의됨 (`ClaudeCodeCLIBackend`, `AnthropicAPIBackend` 두 구현체 존재)
- [ ] CLI 백엔드: 표본 5종목 호출 검증 (필수, 실패 ≤ 1건)
- [ ] API 백엔드: 단위 테스트(mock)로 추상화 검증 완료. 실제 SDK 호출은 (a) Phase 1 후반 사용자 결정 시 (b) ADR-012 §3.3 약관 위반 징후 시 또는 (c) ADR-013 백엔드 전환 결정 시 수행 (Phase 1.1.4-c, 2026-04-29 결정)
- [ ] 응답이 `AnalysisResult` 스키마 준수
- [ ] `llm_calls` 테이블에 호출 로그 기록 (CLI는 cost_usd NULL OK)
- [ ] `daily_analysis_kr` 또는 `daily_analysis_us`에 결과 행 생성
- [ ] (5) 프롬프트 v1 확정 (`prompts/analyze_chart_v1.md` commit)
- [ ] `phase1_progress.md`에 1.1 종료 보고 작성

**사용자 결정 포인트**: 응답 품질이 만족스럽다고 판단 → 1.2 진행 승인

#### 1.2 게이트 ((6) + 정량 검증)

- [ ] (6) 프롬프트 v1 확정 (`prompts/calculate_entry_params_v1.md` commit)
- [ ] `EntryParams` Pydantic 모델 + 검증 (stop_loss_pct 범위 등)
- [ ] 표본 entry 종목 5건 이상에 대해 (6) 호출 성공
- [ ] 산출 파라미터(피봇·손절·비중)가 차트 상 합리적 (사용자 검토)
- [ ] `daily_analysis_*.entry_params` JSON이 GLOSSARY 스키마 일치
- [ ] (5)→(6) 연속 호출이 `run_single_symbol.py --with-entry-params`로 작동
- [ ] `phase1_progress.md`에 1.2 종료 보고 추가

**사용자 결정 포인트**: 진입 파라미터가 신뢰할 만하다 → 1.3 진행 승인

#### 1.3 게이트 (배치 + 7거래일 검증) — Phase 1 종료 게이트

- [ ] `run_daily_analysis.py` 작동 (KR/US 분리, 상한, 캐싱, dry-run, force-recompute 모두)
- [ ] `run_analysis_today.ps1` 래퍼 스크립트 작동
- [ ] 일일 호출 상한이 정확히 작동 (한도 초과 시 중단)
- [ ] 캐싱이 정확히 작동 (재실행 시 skip)
- [ ] 부분 실패 처리 작동 (실패 종목 스킵, 나머지 진행)
- [ ] `show_cost_summary.py` 작동
- [ ] 운영 환경에 Q-003 적용 완료 (실제 운영 PC에서 정상 실행)
- [ ] **7거래일 누적 데이터 확보** (KR + US 합쳐 ≥ 50개 분석 행)
- [ ] 사용자 정성 평가: "쓸만하다"
- [ ] 헌법 §2.1, §2.2, §2.5 위배 없음
- [ ] Q-001, Q-002, Q-003 모두 "완료된 작업" 섹션으로 이동
- [ ] `phase1_progress.md`에 Phase 1 종료 보고 작성

**사용자 결정 포인트**: Phase 1 종료 → Auditor 세션으로 헌법 감사 → Phase 2 brief 작성 단계로

### 9.2 정성 평가 기준 (1.3 사용자 검토)

7거래일 누적 결과를 사용자가 검토할 때, 다음 관점으로 평가:

#### 분류의 합리성
- `entry`로 분류된 종목 표본 10개를 차트로 직접 봤을 때, 사용자가 "납득 가능한" 비율이 얼마인가?
- "납득 가능"의 기준: 최소 베이스 7주 이상, 적절한 패턴, 과도한 RS 위험 없음, 명확한 피봇 식별 가능
- 목표: 70% 이상 납득

#### `watch` 분류의 활용성
- `watch` 종목들이 1~4주 후 실제 entry 후보로 발전하는가? (장기 관찰 필요, Phase 1에서는 일주일 표본만)
- 목표: 사용자가 "재방문할 가치 있다"고 느끼는 watch가 절반 이상

#### `ignore` 분류의 정당성
- `ignore` 종목 표본이 실제로 미너비니 부적합한 이유가 reasoning에 명확히 적혀 있는가?
- 목표: reasoning이 빈약하지 않고 (단순 "no clear pattern" 같은 게 아니라) 구체적 근거를 제시

#### confidence의 일관성
- confidence 0.85+ 종목이 0.55~0.65 종목보다 실제로 더 나은 셋업인가?
- 목표: confidence 분포가 사용자의 직관과 정렬됨

#### `entry_params`의 실행 가능성
- 산출된 pivot_price가 차트 상 명확한 저항선이거나 베이스 고점인가?
- stop_loss_pct가 7~8% 룰을 따르는가? 없으면 그 사유가 risk_flags로 설명되는가?
- 목표: 각 entry 종목의 entry_params가 사용자 트레이딩 결정에 직접 사용 가능

### 9.3 헌법 부합 확인 (Auditor 세션)

Phase 1 종료 시 새 웹 Claude 세션(Auditor)으로 다음을 확인:

#### §2.1 LLM은 직접 주문 실행 안 함
- 코드 전체에서 외부 거래 API 호출 흔적 검사 → 없어야 함
- `daily_analysis_*.entry_params`가 자동으로 `order_reservations`로 흘러가지 않음을 확인 (`order_reservations` 테이블 자체가 Phase 6까지 미존재)

#### §2.2 결정론 코어와 LLM 레이어 물리적 분리
- `apps/llm-analysis/`가 `apps/ingest-databatcher/`의 함수를 import하지 않음 (DB만 공유)
- `apps/ingest-databatcher/`가 `apps/llm-analysis/`를 호출하지 않음

#### §2.5 모든 LLM 출력 영구 보존
- 모든 (5)/(6) 호출이 `llm_calls`에 기록되는지 표본 확인
- request_payload, response_payload가 비어있지 않은지

#### §3.1 4계층 의존성 단방향
- 계층 2(`llm-analysis`)가 계층 1(`ingest-databatcher`)의 출력만 읽고, 계층 1 코드를 수정하지 않음

#### §4 사용자 통제권/이해
- LLM 판단이 자동으로 매매로 이어지는 경로 없음
- reasoning 필드가 모든 분석 결과에 채워짐 (사용자가 "왜?"를 물을 수 있음)

Auditor가 위 항목 모두에 대해 PASS 보고서 작성. `_meta/phases/phase1_audit.md`로 저장.

---

## §10. Builder 세션에 전달할 프롬프트

본 brief가 사용자 승인을 받은 후, 새 Claude Code 세션(개발 환경, Mac)을 열어 다음 프롬프트를 첫 메시지로 사용한다.

Phase 1은 1.1 → 1.2 → 1.3 세 단계로 진행되며, 각 단계 종료 시 사용자가 결과를 검토하고 다음 단계 진행을 승인한다 (§3.4 단계 간 게이트).

### 10.1 1.1 단계 시작 프롬프트

```
이 세션은 미너비니 반자동 트레이딩 보조 시스템의 Phase 1 구현 (Builder 세션) 1.1 단계다.
역할은 ADR-005가 정의한 "Builder" — 일상적 개발 작업과 phase1_progress.md 갱신을 담당한다.
다른 _meta/ 거버넌스 문서는 수정하지 않는다 (불일치 발견 시 보고만).

## 0. 컨텍스트 복원 (필수)

먼저 다음 거버넌스 문서를 순서대로 읽어 컨텍스트를 복원하라:

1. _meta/06_CURRENT_STATE.md — 현재 위치
2. _meta/00_CONSTITUTION.md — 절대 원칙 (특히 §2.1, §2.2, §2.5)
3. _meta/01_ARCHITECTURE.md — 4계층 구조, 계층 2 LLM 분석 위치
4. _meta/04_DECISIONS.md — ADR-005 (거버넌스), ADR-009 (스키마), ADR-010 (운영 큐), ADR-011 (CLI 백엔드), ADR-012 (자동 트리거)
5. _meta/05_GLOSSARY.md — Part B.1.7 (daily_analysis, llm_calls), Part B.2 (JSON 스키마), Part B.3 (함수 시그니처), Part C (LLM 백엔드)
6. _meta/operational_queue.md — Q 항목 양식, 환경 정보
7. _meta/phases/phase1_brief.md — 본 Phase의 SSoT. 전체를 정독.
8. CLAUDE.md, README.md — 빌드·실행·테스트 가이드

특히 다음을 머릿속에 정리:
- 헌법 §2.2: 결정론 코어와 LLM 분석 레이어 물리적 분리. apps/llm-analysis/는 apps/ingest-databatcher/ 함수를 import하지 않는다 (DB만 공유).
- 헌법 §2.5: 모든 LLM 호출은 llm_calls 테이블에 영구 보존.
- ADR-011 §2: LLMBackend 추상화 의무. CLI/API 양 구현체.
- ADR-011 §3: CLI 모드 cost_usd NULL 허용 등 백엔드별 필드 채움 정책.
- ADR-012 §3: 자동 트리거 환경의 모니터링 4종 (일일 호출 상한 hard stop 등).
- ADR-010: 마이그레이션 = ① Alembic ② raw SQL ③ 운영 큐 항목 3종 산출물.

## 1. 1.1 단계 작업 범위

phase1_brief.md §3.1의 작업 항목 1.1.1~1.1.15를 순서대로 수행한다.

요약:
1. DB 마이그레이션 3종 산출물 작성 (Alembic + raw SQL + Q-002)
2. apps/llm-analysis/ 디렉토리 골격 (§5.2 구조 그대로)
3. LLMBackend 추상화 인터페이스 + CLI/API 두 구현체
4. llm_calls 기록 wrapper
5. (5) analyze_chart 프롬프트 v1 (§6.2 본문 그대로 옮김, prompts/analyze_chart_v1.md)
6. data_loader, prompt_builder, result_parser, AnalysisResult Pydantic 모델
7. run_single_symbol.py CLI
8. 단일 종목 호출 검증 (CLI 5종목 + API 1종목)
9. 프롬프트 튜닝 5~10회 반복 후 v1 확정

## 2. 진행 원칙

- 각 작업 항목 시작 전에 무엇을 할지 1~2줄로 알려주고 시작.
- DB 변경(마이그레이션 적용)은 개발 환경(Mac)에서만 수행, 운영 환경 적용은 Q-002로 등록만 (사용자가 별도 처리).
- 단일 종목 LLM 호출은 사용자에게 알려준 후 진행 (비용·시간 발생).
- 프롬프트 튜닝 중 새 파일을 만들지 않고 같은 v1 파일을 수정 (§6.5 절차).
- _meta/ 문서와 코드 사이 불일치 발견 시 수정하지 말고 보고만.
- 1.1 단계가 끝날 때 _meta/phases/phase1_progress.md에 종료 보고 작성.

## 3. 검증·승인 게이트 (1.1 게이트)

phase1_brief.md §9.1의 1.1 게이트 체크리스트를 모두 통과해야 1.1 종료. 특히:

- [ ] CLI 백엔드로 표본 5종목 호출 검증 (실패 ≤ 1건)
- [ ] API 백엔드는 단위 테스트(mock)로 추상화 검증 (실제 SDK 호출은 Phase 1.1.4-c 결정으로 미룸)
- [ ] llm_calls 테이블에 호출 로그 기록 (CLI는 cost_usd NULL OK 또는 참고값 저장)
- [ ] daily_analysis_kr 또는 daily_analysis_us에 결과 행 생성
- [ ] AnalysisResult Pydantic 스키마 준수 (classification, confidence, reasoning, pattern, risk_flags)
- [ ] 프롬프트 production version commit (prompts/analyze_chart_v*.md)
- [ ] phase1_progress.md에 1.1 종료 보고

## 4. 1.1 종료 후

1.1 게이트 통과 시:
1. phase1_progress.md에 1.1 종료 보고 작성
2. 사용자에게 결과 보고 (분석 표본 결과 + 응답 품질 평가 의견)
3. 1.2 단계 진행 승인 요청

승인되면 1.2 단계 시작. 본 세션에서 이어서 진행하거나 별도 세션 시작.

## 5. 작업 시작

지금 Step 0 (컨텍스트 복원)부터 시작하라.
완료 후 Step 1 (1.1.1 작업 — DB 마이그레이션 3종 산출물 작성)로 진행할지 승인을 요청하라.
```

### 10.2 1.2 단계 시작 프롬프트 (1.1 종료 승인 후)

위 1.1 프롬프트와 거의 동일한 양식. 변경 부분만:
- "1.1 단계" → "1.2 단계"
- 작업 범위: phase1_brief.md §3.2의 1.2.1~1.2.8
- 검증 게이트: §9.1의 1.2 게이트
- 핵심 산출물: prompts/calculate_entry_params_v1.md, EntryParams Pydantic 모델, run_single_symbol.py에 --with-entry-params 추가

상세 내용은 1.1 종료 후 사용자가 본 brief를 보면서 동일 양식으로 작성.

### 10.3 1.3 단계 시작 프롬프트 (1.2 종료 승인 후)

가장 큰 단계. 다음을 강조:
- §3.3의 1.3.1~1.3.11 (특히 자동 트리거·캐싱·dry-run·Task Scheduler 등록)
- ADR-012 §3 모니터링 4종 구현 (§8.4)
- Task Scheduler 등록 절차 (§8.3) → Q-003으로 등록
- 7거래일 누적 후 사용자 검토 (§9.2 정성 평가 기준)
- Phase 1 종료 게이트 (§9.1 1.3 게이트)

### 10.4 Builder 세션 운영 원칙

세 단계 모두에 공통 적용:

1. **Architect/Builder 분리 (ADR-005)**: Builder는 phase1_progress.md만 자유롭게 수정. 다른 _meta/ 문서는 불일치 발견 시 보고만.
2. **운영 환경 작업 분리**: 모든 PROD 작업은 Q-NNN 항목으로 등록. Builder는 DEV(Mac)에서만 직접 작업.
3. **마이그레이션 3종 산출물 (ADR-010)**: 새 스키마 변경 시 ① Alembic 파일 ② raw SQL 파일 ③ 운영 큐 항목 모두 작성.
4. **LLM 호출 기록 (헌법 §2.5)**: CLI 백엔드라도 llm_calls 테이블에 호출 로그 누락 없이.
5. **부분 실패 허용 (§7.6)**: 배치 실행 중 일부 종목 실패는 전체 중단 사유 아님. 끝까지 진행 후 요약 보고.
6. **헌법 §2.2 준수**: apps/llm-analysis/는 apps/ingest-databatcher/ 함수를 import하지 않는다.

---

## §11. 미해결 질문 / Phase 1 후로 미루는 것

본 Phase에서 의식적으로 다루지 않거나 미정으로 두는 항목을 명시한다. 누락이 아니라 **의도적 비포함**임을 분명히 한다.

### 11.1 Phase 1 범위 밖 (다른 Phase에서 결정)

| 항목 | 처리 위치 | 근거 |
|---|---|---|
| Crypto 분석 | 별도 Phase | brief §2.2, 점검 2=A |
| 장중 실시간 분석 | 영구 비목표 | ADR-004 |
| 백테스트 (Phase 5 종료 조건) | Phase 5 | ROADMAP, 헌법 §2.3 |
| 이메일 발송 | Phase 2 | ROADMAP |
| AI 카드 UI / "왜?" 버튼 | Phase 3 | ROADMAP |
| Q&A 에이전트 | Phase 4 | ROADMAP |
| 자동 주문 엔진 | Phase 6 | 헌법 §2.4, ROADMAP |
| 포트폴리오 매니저 | Phase 7 | ROADMAP |
| 매매 통계 | Phase 8 | ROADMAP |
| `failed_reason` 컬럼 활용 (스크리너 탈락 종목 저장) | Phase 6 이후 | phase0_alignment_review.md §5 |

### 11.2 영구 비목표 (헌법 §6 또는 명시적 거부)

| 항목 | 근거 |
|---|---|
| 고빈도 거래 (HFT) | 헌법 §6 |
| 다른 사용자에게 판매하는 SaaS | 헌법 §6 |
| 모든 시장 범용화 (현재는 KOSPI/KOSDAQ/NYSE/NASDAQ + Crypto만) | 헌법 §6 |
| AI 자율 시스템 (사용자 통제권 양도) | 헌법 §6 |
| 프롬프트 자동 진화 / RLHF | brief §2.2, 헌법 §4.1 통제권 |
| 다중 모델 비교 / A·B 테스트 | brief §2.2, Phase 5 또는 별도 R&D |

### 11.3 향후 재검토 가능 항목 (Phase 1 운영 결과에 따라)

#### 11.3.1 Vision API 도입 (이미지 차트 입력)

- 현재 결정 (§6.1): 텍스트 기반 입력만. 이미지 미포함.
- 재검토 트리거: Phase 5 백테스트에서 텍스트 분석 정확도 부족 판명
- 비용 영향이 크므로 반드시 ADR로 결정

#### 11.3.2 52주 고가/저가, volume_ma20의 인디케이터 영구화

- 현재 결정 (brief §2.2): LLM 호출부에서 즉석 계산
- 재검토 트리거: Phase 5 백테스트 시 과거 시점 복원 편의성 필요
- 인디케이터 long-form(ADR-006) 스키마에 추가하면 됨

#### 11.3.3 LLM 백엔드 전환 (CLI → API)

- 현재 결정 (ADR-011, ADR-012): CLI 기본 + 자동 트리거 + 모니터링
- 재검토 트리거 (ADR-011 §5 + ADR-012 §6):
  - (a) Phase 5 백테스트 결과 (시스템이 가치를 입증하면 API 전환)
  - (b) 2026-10-24 시점 도달
  - (c) Anthropic 약관 또는 정책의 의미 있는 변경
  - (d) 사용자 판단
  - (e) 약관 위반 징후 관측 (즉시 전환)
- 전환 시 새 ADR 작성, ADR-012는 Superseded

#### 11.3.4 자동 트리거 시각 조정

- 현재 결정 (ADR-012 §2): US 16:00 KST / KR 21:00 KST
- 재검토 트리거:
  - daily cron 시각 변경 시 (현재 US 08:00 / KR 19:00)
  - daily 소요 시간 변동 시 (특히 US daily 6시간 이슈, §11.3.5 참조)
  - LLM 분석 소요가 예상보다 길어 다음 윈도우 침범 시
- 변경 시 Task Scheduler 갱신 + settings.yaml 갱신 + 큰 변경이면 ADR 후속 (§8.2 SSoT 정책)

#### 11.3.5 US daily 소요 시간 최적화 (별도 백로그)

- 현재 상태: US daily가 매 회 약 6시간 소요 (사용자 식별)
- 영향: ADR-012의 안전 마진 산정에 직접 영향. US daily가 더 빨라지면 LLM 트리거 시각도 앞당길 수 있음.
- 처리: Phase 1 범위 밖. `_meta/06_CURRENT_STATE.md` 미해결 이슈 §F로 등록됨. 별도 시점에 다룸.

### 11.4 Phase 1 운영 중 발견될 가능성 있는 이슈 (사전 인지)

다음 이슈들은 Phase 1 1.3 단계 7거래일 누적 검증 중 발견될 가능성이 있다. 발견 시 처리 방향:

| 가능성 있는 이슈 | 처리 방향 |
|---|---|
| LLM이 entry 분류를 너무 적게/많이 함 | 프롬프트 v2 튜닝 (1.1로 일부 회귀) |
| confidence 분포가 사용자 직관과 어긋남 | 프롬프트 reasoning 강화 |
| 일부 종목에서 응답 파싱 실패 반복 | result_parser 보강 + 프롬프트 제약 강화 |
| Max 플랜 5시간 윈도우 한도 자주 도달 | ADR-012 §3.3 트리거 → API 전환 검토 |
| CLI/API 응답 품질 차이 큼 | ADR-011 §2 추상화 점검 + 모델 통일 검토 |
| Task Scheduler 트리거 시각이 daily cron과 충돌 | 시각 조정 (§11.3.4 재검토) |
| 분석 소요가 1시간 이상 일관되게 김 | 동시성 도입 검토 (Phase 1 종료 후 별도 ADR) |

발견 시 `phase1_progress.md`에 기록 + 사용자와 처리 방향 협의.

### 11.4-bis Phase 1.2 트랙 B에서 실제 발견된 이슈와 처리 방향

§11.4가 추정 표라면 본 항목은 1.2 트랙 B 진행 중 **실제로 발견된 이슈**다. 1.3 진입 전후 또는 1.3 누적 검증 중 처리됐고, **본 4 항목 모두 Phase 1 종료 시점에 처리 결과를 본문 통합한다 (2026-05-09)**.

#### 11.4-bis.1 (5) v2 분류 보수성 — 1.3 누적 평가 결과 (Phase 2 sprint로 이관)

**배경**: B.5.5 NVST를 entry로 분류한 v2 결정에 대해 두 번째 Evaluator(운영자 시각)가 진입 보류 권고. 4가지 약점:
1. Breakout 거래량 1.03× (책 기준 1.4× 미달)
2. RS 81 (preferred 90+ 아님)
3. 400 sample 중 lone signal (leadership group 부재)
4. Catalyst 시점 5주 전 (모멘텀 식음)

**의심**: v2가 약한 setup도 entry로 통과시키는 보수성 부족 가능. 단 1건 표본으로 systemic 판정 불가.

**Phase 1.3 운영 결과 (2026-05-08, 167행 누적)**:
- entry 분류: **0건** (KR 70 + US 97에서 모두 watch/ignore/timeout)
- 해석: B.5.5 자연 발생률(0.25%) × 167행 = expected 0~1건 → 통계적으로 정합. froth 시장 환경(2026-04~05)도 정합. **systemic 보수성 부족으로 판정할 표본 부재** — 오히려 v2 보수성이 시장 환경과 부합한 것일 수 있음.
- 대체 평가: Evaluator 1차 평가에서 표본 7건(NVDA·VRT·NVMI·CDNS×2·HOOD·ALTO) 100% "합리적" 검증. ignore reasoning에서 구체 수치 + 미너비니 원칙 명시 일관 적용 확인.

**처리**: **Phase 2B Sprint "entry-side 평가" + "(5) prompt v3 검토"로 이관**. 자연 누적 데이터(Phase 2 시장 환경에서 entry 발생)에서 §9.2 기준 1 (entry 10개 70%+) 정식 충족 + systemic 평가 → v3 작업 여부 결정. 06_CURRENT_STATE 미해결 이슈 §K 참조.

#### 11.4-bis.2 (6) 함수 v1.1 fix 3가지 — 완료 (Phase 1.3.0)

**배경**: NVST B.5.5 1차 Evaluator 평가에서 (6) 함수의 표기·투명성 문제 3가지 도출.

**항목**: 본 brief §6.3 "v1.1 production lock 결과" §2 표 참조.

**Phase 1.3.0 처리 결과 (commit `7a1dd98`, 2026-05-07)**: ✅ **완료**
1. ✅ dual stop_pct 분리 (`stop_loss_pct_from_pivot` rename + `stop_loss_pct_from_current_price` 신규 + auto-emit warning)
2. ✅ `trigger_price` schema-level 분리 (pivot raw + trigger buffered 둘 다 emit)
3. ✅ `observed_breakout_volume_ratio` 신규 + auto-emit warning

EntryParams 13 → 16필드, KnownWarning enum 10 → 12종 (auto-emit 2종 추가). 단위 테스트 53/53 통과 + NVST 합성 검증 6/6 OK. 06_CURRENT_STATE 미해결 이슈 §L 해소.

#### 11.4-bis.3 ETF 잘못 통과 — ADR-015로 처리됨 (해소)

**배경**:
- B.5.5 sample 6건 (EMF, RMT, CEE×2, KF, CAF) — closed-end fund 계열
- Phase 1.3.10 자연 운영 12건 (VRTL, SOXL, MVLL, MUU, MULL, AMDG, AMDL, AMUU, KORU, INTW, DLLL, BWET) — leveraged ETF 다수, Q-004 등록

**해석 (확장됨)**: us_symbol_master의 symbol_type 분류가 외부 소스(FDR/yfinance) 단계에서 부정확. closed-end fund / leveraged ETF / 신규 ETF / preferred stock·ADR 등이 STOCK으로 등록됐을 가능성.

**처리 (2026-05-09)**: ✅ **ADR-015 채택으로 정책 명문화 + Phase 2 sprint로 구현 이관**
- ADR-015 §1: Fund Vehicle 4 카테고리 명확화 (ETF / Leveraged ETF / CEF / ADR)
- ADR-015 §2: us_sync_symbol_master.py 보강 (다중 소스 cross-check + 휴리스틱 + override 테이블 신설) — Phase 2B Sprint
- ADR-015 §3: Q-004 적용 절차 보강 (일괄 ETF 처리 후 Phase 2 sprint에서 세분화 정정)
- ADR-013 §3 안전망 (LLM Pre-Check) 그대로 계승

06_CURRENT_STATE 미해결 이슈 §J 해소.

#### 11.4-bis.4 분류 불안정 — Phase 1.3 추가 사례 (Phase 2 sprint 모니터링)

**배경 (B.5.5)**: EA 종목이 3회 평가 모두 다른 결과 (1/13 watch → 1/14 ignore → 1/15 timeout).

**Phase 1.3 추가 사례 (2026-05-08)**:
- ALTO 4시점 toggle: 4/28 ignore conf=0.75 → 5/1 watch 0.75 → 5/4 ignore 0.80 → 5/6 ignore 0.90
- NVST 추가 사례: B.5.5 entry → 2026-05-07 ignore (1.3.0 v1.1 검증 합성 호출, 약 4개월 후)
- 기타 multi-evaluated 종목들 일부 toggle 관찰

**해석 가능성**:
- 시장 변화로 실제 분류 변동 (정상) — ALTO의 경우 conf 점진 증가는 일관성 패턴
- v2 응답 일관성 부족 (LLM 자체 노이즈)
- 분류 경계 정량화 미흡 — `phase1_classification_logic_review.md` §1.2 "watch vs ignore 경계 모호 케이스" 정합

**처리**: **Phase 2B Sprint "분류 안정성 모니터링" + "(5) prompt v3"으로 이관**. 자연 누적 데이터에서 multi-evaluated 종목의 분류 일관성 정량 측정 (예: revisit_condition 필드 추가 검토, watch ↔ ignore toggle 빈도 통계, conf 변화 추적). 06_CURRENT_STATE 미해결 이슈 §M 참조.

### 11.5 본 brief에서 의식적으로 두루뭉술하게 둔 부분

- **프롬프트 v1의 정확한 텍스트**: §6.2/§6.3에 본문이 있으나, Builder가 1.1 단계에서 5~10회 튜닝하며 다듬을 것. 문서는 v1 확정 후 commit.
- **Anthropic 모델 버전 (claude-sonnet-4-5 등)**: settings.yaml 기본값. 사용자가 운영 중 변경 가능. ADR로 추적 안 함 (모델 버전 갱신은 ADR 사항이 아님).
- **운영 PC 경로 (`C:\path\to\DataBatcher`)**: Q-003에서 사용자가 실제 경로로 치환.
- **주간 점검 시점**: 사용자 일정에 따라. brief는 "주 1회" 권장만.

이 항목들은 Builder가 합리적 기본값을 채워넣고 Architect 세션이 후속에서 갱신.

---

## 마무리

본 brief는 Phase 1 — LLM 분석 레이어 구축의 SSoT다. 사용자 승인 후 Builder 세션에서 §3.1 → §3.2 → §3.3 순으로 진행한다.

### Builder 세션 진입 절차

1. **사용자가 본 brief를 검토하고 commit**
2. **(이미 완료) Q-001 운영 환경 적용** ✅ 2026-04-26 18:18 KST
3. **개발 환경(Mac)에서 새 Claude Code 세션 시작**
4. **§10.1의 1.1 단계 시작 프롬프트를 첫 메시지로 사용**
5. **1.1 단계 진행 → 사용자 검토 → 1.2 → 사용자 검토 → 1.3 → Phase 1 종료 게이트 → Auditor 세션**

### Phase 1 종료 후

- Auditor 세션 (별도 웹 Claude)이 헌법 부합 여부 평가 (§9.3)
- `phase1_audit.md` 작성
- 통과 시 Phase 2 brief 작성으로 진행 (메일 발송 모듈)

### 본 brief 갱신 정책

- 1.1 단계에서 발견된 작은 문제 (변수명, 디렉토리 위치 등): Builder가 phase1_progress.md에 기록 + 1.1 종료 시 Architect 세션에서 brief 갱신
- 큰 결정 변경 (백엔드 전환, 트리거 시각 변경 등): 새 ADR 작성 + brief 갱신
- 본 brief 자체는 Phase 1 종료 시점의 SSoT를 유지하며, 변경 이력은 ADR로 추적

---

*본 brief는 ADR-001~012의 누적된 결정을 Phase 1 구현 가능 형태로 통합한 문서다. Builder는 본 brief를 따르되, 의문 발생 시 ADR 원본을 참조한다.*

---