# 용어집 및 인터페이스 정의

> 이 문서는 프로젝트에서 사용하는 용어와 모듈 간 인터페이스(데이터 스키마)를 정의한다.  
> **모듈 간 유기적 연결의 핵심이 되는 문서**이다. 새 모듈을 만들 때 반드시 이 문서를 참조한다.  
> 인터페이스 변경 시 ADR을 작성하고, 영향받는 모듈 목록을 명시한다.
>
> **이 문서는 현재 실제 DB 구조를 반영한다.** 설계 이상(ideal)이 아니라 실제(reality)를 기록하며, 개정은 실제 스키마 변경과 동기화되어야 한다.

---

## Part A: 도메인 용어

### 미너비니 트레이딩 용어

**미너비니 템플릿 (Trend Template)**: Mark Minervini가 정의한 8가지 조건. 강한 상승 추세에 있는 종목을 필터링하기 위한 규칙. 본 시스템의 구현은 Part B.2 `conditions_met` 스키마 참조.

**RS Rating (Relative Strength Rating)**: 종목의 가격 모멘텀을 시장 전체 종목 대비 백분위로 표시 (1~99). IBD에서 사용. 본 시스템은 3m/6m/9m/12m 수익률 가중 평균(0.4/0.2/0.2/0.2)을 cross-sectional 백분위로 계산.

**RS Line**: 종목 가격을 벤치마크(보통 S&P 500 또는 KOSPI)로 나눈 비율의 시계열. 우상향이면 시장 대비 강세.

**Blue Dot**: RS Line은 52주 신고가지만 가격은 52주 신고가가 아닌 상태. 상대강세가 선행 형성된 신호.

**VCP (Volatility Contraction Pattern)**: 베이스 형성 과정에서 변동성이 점차 수축하는 패턴. 미너비니의 핵심 진입 패턴.

**Pivot Point (피봇 포인트)**: 베이스의 최근 고점 + 약간의 마진. 이를 돌파할 때 진입 신호.

**Base (베이스)**: 가격이 일정 범위에서 횡보하며 매물 소화가 일어나는 구간.

**Stage Analysis (스테이지 분석)**: 종목 가격 사이클을 4단계로 분류. Stage 1(저점 베이스), Stage 2(상승), Stage 3(고점 분배), Stage 4(하락).

### 시스템 용어

**계층 (Layer)**: 시스템의 4개 구조적 계층. 1=결정론적 코어, 2=LLM 분석, 3=자동화, 4=에이전트.

**모듈 (Module)**: 12개 요구사항 각각. (1)~(12)로 번호 부여.

**승인 게이트 (Approval Gate)**: LLM 판단이 실제 매매로 이어질 때 사용자 확인이 필요한 지점.

**페이퍼 트레이딩 (Paper Trading)**: 실제 주문 대신 가상 체결만 기록하는 모드. 실거래 전 검증용.

**Circuit Breaker**: 시스템 오류 감지 시 자동 주문을 중단시키는 안전 장치.

### 용어 통일 규칙

**Symbol vs Ticker**: 본 시스템은 **`symbol`을 표준 용어로 사용**한다. 외부 문서에서 "ticker"로 표현된 것은 모두 symbol로 읽는다. 스키마 컬럼명도 `symbol`.

**Region vs Market**:
- **Region**: 국가/대분류. 값: `"KR"`, `"US"`. 주로 API·프론트·`minervini_list_selection` 등 사용자 관점에서 씀.
- **Market**: 거래소·세부 분류. 값: `"KOSPI"`, `"KOSDAQ"`, `"ETF"`(KR·US 공통), `"NYSE"`, `"NASDAQ"`. 주로 데이터 적재·스크리닝·인디케이터 테이블에서 씀.
- `region`과 `market`은 1:N 관계 (KR은 KOSPI/KOSDAQ/ETF로 분기됨).

**Params Hash**: 인디케이터·스크리너 파라미터 세트의 해시값(SHA1 40자). 같은 인디케이터라도 파라미터가 다르면 별개 레코드로 구분하기 위함.

**Screen Config Hash**: 미너비니 스크리닝 설정(필터 on/off, 임계값 등) 전체의 해시값. 설정이 변경되면 과거 결과와 신규 결과가 섞이지 않도록 분리 저장.

---

## Part B: 데이터 스키마

### B.0 테이블 구조 개요

본 시스템의 DB는 **실사용 기반의 분리 구조**를 따른다:

- **OHLCV / 인디케이터**: 시장별·타임프레임별로 테이블이 분리됨 (precision·필드 요구사항이 다름)
- **인디케이터 저장 방식**: **long-form** (`symbol, date, indicator, params_hash, value`)으로 확장 가능한 구조. Wide-form 조회는 `v_*_price_with_ma` 뷰를 통해 제공.
- **스크리닝 결과**: 시장별로 분리 (KR/US). `screen_config_hash`로 설정 버전 관리.
- **LLM 분석 결과**: 시장별로 분리 (Phase 1에서 생성). 스크리닝 결과와 동일한 `(symbol, date)` PK 패턴.

이 구조의 채택 배경은 ADR-006, ADR-007, ADR-008을 참조.

### B.1 DB 테이블 스키마

#### B.1.1 가격 데이터 (OHLCV)

가격 데이터는 **시장별로 5개 테이블**로 분리. Weekly 테이블은 동일 구조에 `week_start, week_end`로 PK 변경.

##### `stock_prices` (KR 주식 일봉)
```sql
CREATE TABLE stock_prices (
  symbol        VARCHAR(32)  NOT NULL,
  date          DATE         NOT NULL,
  open          DECIMAL(18,4),
  high          DECIMAL(18,4),
  low           DECIMAL(18,4),
  close         DECIMAL(18,4),
  adj_close     DECIMAL(18,4) NULL,
  volume        BIGINT,
  market        VARCHAR(16) NOT NULL,   -- 'KOSPI' | 'KOSDAQ' | 'ETF'
  source        VARCHAR(16) NOT NULL,   -- 'pykrx' | 'fdr' 등
  etl_loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (symbol, date),
  KEY idx_date (date),
  KEY idx_market_date (market, date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

##### `us_stock_prices` (US 주식 일봉)
구조는 `stock_prices`와 동일. `market` 값만 `'NYSE' | 'NASDAQ' | 'ETF'`.

##### `kr_index_prices`, `us_index_prices` (지수)
`adj_close` 컬럼 없음. 나머지 동일.

##### `crypto_prices_daily` (크립토)
```sql
CREATE TABLE crypto_prices_daily (
  symbol        VARCHAR(32)  NOT NULL,
  date          DATE         NOT NULL,
  open          DECIMAL(28,10) NULL,    -- 크립토는 소수점 정밀도 크게
  high          DECIMAL(28,10) NULL,
  low           DECIMAL(28,10) NULL,
  close         DECIMAL(28,10) NULL,
  volume_quote  DECIMAL(28,10) NULL,    -- 주식과 달리 quote 기준 거래량
  exchange      VARCHAR(16)  NOT NULL,  -- 'BINANCE'
  source        VARCHAR(16)  NOT NULL,
  etl_loaded_at TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (symbol, date),
  KEY idx_date (date),
  KEY idx_symbol_date (symbol, date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

##### Weekly 테이블들
각 일봉 테이블마다 `_weekly` 버전 존재 (`stock_prices_weekly`, `us_stock_prices_weekly`, `kr_index_prices_weekly`, `us_index_prices_weekly`, `crypto_prices_weekly`). PK는 `(symbol, week_start)`, 추가 컬럼 `week_end DATE`.

#### B.1.2 인디케이터 (long-form)

인디케이터는 **시장별 테이블 + long-form** 구조. 하나의 행이 `(심볼, 날짜, 지표, 파라미터)` 조합 하나의 값을 나타냄.

##### `stock_indicators` (KR 일봉 인디케이터)
```sql
CREATE TABLE stock_indicators (
  symbol        VARCHAR(32) NOT NULL,
  date          DATE        NOT NULL,
  indicator     VARCHAR(64) NOT NULL,   -- 'sma_50_close', 'rs_line', 'rs_rating', 'blue_dot' 등
  params_hash   CHAR(40)    NOT NULL,   -- 파라미터 세트 SHA1
  value         DECIMAL(28,10) NULL,
  market        VARCHAR(16) NOT NULL,
  source        VARCHAR(16) NOT NULL,
  etl_loaded_at TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (symbol, date, indicator, params_hash),
  KEY idx_indicator_date (indicator, date),
  KEY idx_symbol_date (symbol, date),
  KEY idx_indicator_date_market_symbol (indicator, date, market, symbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

##### 다른 시장/타임프레임
동일 구조로 각 시장별·타임프레임별 존재:
- `us_stock_indicators`, `us_stock_indicators_weekly`
- `stock_indicators_weekly`
- `kr_index_indicators`, `kr_index_indicators_weekly`
- `us_index_indicators`, `us_index_indicators_weekly`
- `crypto_indicators_daily`, `crypto_indicators_weekly`

##### Wide-form 조회는 뷰 사용

```sql
CREATE VIEW v_stock_price_with_ma AS
SELECT p.symbol, p.date, p.open, p.high, p.low, p.adj_close AS close, p.volume,
  MAX(CASE WHEN i.indicator = 'sma_50_close'  THEN i.value END) AS sma_50,
  MAX(CASE WHEN i.indicator = 'sma_100_close' THEN i.value END) AS sma_100,
  MAX(CASE WHEN i.indicator = 'sma_150_close' THEN i.value END) AS sma_150,
  MAX(CASE WHEN i.indicator = 'sma_200_close' THEN i.value END) AS sma_200,
  MAX(CASE WHEN i.indicator = 'rs_line'       THEN i.value END) AS rs_line
FROM stock_prices p
LEFT JOIN stock_indicators i ON p.symbol = i.symbol AND p.date = i.date
GROUP BY p.symbol, p.date, p.open, p.high, p.low, p.close, p.volume;
```

뷰 목록: `v_stock_price_with_ma`, `v_stock_price_weekly_with_ma`, `v_us_stock_price_with_ma`, `v_us_stock_price_weekly_with_ma`, `v_crypto_price_weekly_with_ma`, `v_kr_index_price_with_ma`, `v_us_index_price_with_ma`.

**현재 영구 저장되지 않는 지표** (스크리너가 즉석 계산):
- 52주 고가/저가
- 거래량 20일 이동평균

Phase 1 LLM 호출 시 필요하면 호출부에서 즉석 계산하거나, 필요 시 ADR로 영구화 결정.

#### B.1.3 심볼 마스터

각 시장별로 분리:

##### `symbol_master` (KR 주식)
```sql
CREATE TABLE symbol_master (
  symbol        VARCHAR(32) PRIMARY KEY,
  market        VARCHAR(16) NOT NULL,
  symbol_type   VARCHAR(16) NULL,
  name          VARCHAR(128) NULL,
  status        VARCHAR(16) NOT NULL,
  sector        VARCHAR(128) NULL,
  sector_detail VARCHAR(256) NULL,
  industry      VARCHAR(512) NULL,
  sector_source VARCHAR(32) NULL,
  sector_updated_at TIMESTAMP NULL,
  first_date    DATE NULL,
  last_date     DATE NULL,
  updated_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_market_status_sector_name (market, status, sector, name),
  KEY idx_market_status_sector_symbol (market, status, sector, symbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

##### 다른 시장
- `us_symbol_master`: 구조 유사, `name`은 VARCHAR(256), `industry`는 VARCHAR(128)
- `crypto_symbol_master`: 구조 단순 (`symbol, base_asset, quote_asset, status, exchange`)
- `kr_index_master`, `us_index_master`: `(symbol, market, name, status)`만

#### B.1.4 운영 / 로그

##### `sync_log` (모든 ETL 작업 로그)
```sql
CREATE TABLE sync_log (
  id            BIGINT AUTO_INCREMENT PRIMARY KEY,
  job_name      VARCHAR(64) NOT NULL,
  market        VARCHAR(16) NOT NULL,
  symbol        VARCHAR(32) NULL,
  start_time    DATETIME NOT NULL,
  end_time      DATETIME NULL,
  rows_processed INT DEFAULT 0,
  status        VARCHAR(16) NOT NULL,   -- 'success' | 'failed' | 'running' 등
  message       VARCHAR(1024) NULL,
  created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_job_market_time (job_name, market, start_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

##### `kr_sector_snapshot` (섹터 스냅샷, KR 전용)
일별 섹터 집계용. 스키마는 `project_snapshot_phase0.md` 참조. Phase 1에서는 사용하지 않음.

#### B.1.5 미너비니 스크리닝 결과

##### `minervini_screen_results_kr` / `minervini_screen_results_us`

**Phase 1 착수 직전에 `conditions_met` JSON 컬럼 추가**됨 (ADR-009 결정 3 반영). 추가 후 스키마:

```sql
CREATE TABLE minervini_screen_results_kr (
  symbol             VARCHAR(32)  NOT NULL,
  date               DATE         NOT NULL,
  market             VARCHAR(16)  NOT NULL,   -- 'KOSPI' | 'KOSDAQ' | 'ETF'
  rs_rating          DECIMAL(5,1) NULL,
  is_blue_dot        TINYINT      NULL,
  conditions_met     JSON         NULL,       -- ★ Phase 1 착수 전 ALTER로 추가
  screen_config_hash CHAR(40)     NOT NULL,
  failed_reason      VARCHAR(512) NULL,       -- dead column (현재 사용 안 함, 정책상 통과 종목만 INSERT)
  created_at         TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (symbol, date, screen_config_hash),
  KEY idx_date_market_config (date, market, screen_config_hash),
  KEY idx_date_market_symbol (date, market, symbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

US 버전(`minervini_screen_results_us`)은 `market` 값만 `'NYSE' | 'NASDAQ' | 'ETF'`로 다름.

**정책**:
- **통과 종목만 INSERT** (탈락 종목은 저장 안 함) — ADR-008 참조.
- 설정 변경 시 `screen_config_hash` 변경 → 자동으로 별개 레코드 세트 생성.
- `conditions_met` JSON 스키마는 Part B.2 참조.

#### B.1.6 사용자 선택 상태

##### `minervini_list_selection` (현역, trading-view-project 전용)
```sql
CREATE TABLE minervini_list_selection (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  region VARCHAR(8) NOT NULL,            -- 'KR' | 'US'
  `date` DATE NOT NULL,
  market VARCHAR(32) NOT NULL,
  symbol VARCHAR(32) NOT NULL,
  list_type VARCHAR(16) NOT NULL,        -- 'focus' | 'action' | 'pass'
  trigger_price DECIMAL(18,4) NULL,
  stop_price DECIMAL(18,4) NULL,
  status_tag VARCHAR(32) NULL,           -- 'A' | 'B' | 'C' | 'D' | 'E'
  memo TEXT NULL,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_minervini_list_selection (region, `date`, market, symbol),
  KEY idx_minervini_list_selection_lookup (region, `date`, list_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

##### `watchlist_items` (legacy, 사용 안 함)
과거 설계의 잔존 테이블. 스키마는 DB에 남아있으나 현재 로직에서 호출되지 않음. Phase 6에서 `order_reservations` 설계 시 제거 또는 통합 결정 예정.

#### B.1.7 LLM 분석 결과 (Phase 1 신설)

##### `daily_analysis_kr` / `daily_analysis_us` (신규, Phase 1 첫 마이그레이션에서 생성)

```sql
CREATE TABLE daily_analysis_kr (
  symbol             VARCHAR(32)  NOT NULL,
  date               DATE         NOT NULL,
  market             VARCHAR(16)  NOT NULL,   -- 'KOSPI' | 'KOSDAQ' | 'ETF'
  classification     VARCHAR(20)  NOT NULL,   -- 'entry' | 'watch' | 'ignore'
  confidence         DECIMAL(3,2) NULL,       -- 0.00 ~ 1.00
  reasoning          TEXT         NULL,       -- LLM의 자연어 근거
  pattern            VARCHAR(50)  NULL,       -- 'VCP' | 'flat_base' | 'cup_handle' | 'none' 등
  risk_flags         JSON         NULL,       -- Part B.2 참조
  entry_params       JSON         NULL,       -- Part B.2 참조 (classification='entry'일 때만)
  screen_config_hash CHAR(40)     NULL,       -- 참조한 minervini_screen_results_kr 레코드의 hash
  llm_call_id        BIGINT       NULL,       -- llm_calls 테이블 외래키 (소프트)
  created_at         TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (symbol, date),
  KEY idx_date_class (date, classification),
  KEY idx_date_market (date, market)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

US 버전(`daily_analysis_us`)은 구조 동일. PK 구성 근거는 ADR-009 참조.

##### `llm_calls` (신규, 헌법 §2.5 준수)

```sql
CREATE TABLE llm_calls (
  id                BIGINT PRIMARY KEY AUTO_INCREMENT,
  timestamp         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  module            VARCHAR(50),     -- 'analysis_5_kr' | 'analysis_5_us' | 'analysis_6_kr' | 'agent_8' 등
  model             VARCHAR(50),     -- 'claude-sonnet-4' 등
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

#### B.1.8 Phase 6 이후 도입 예정 테이블

아래 테이블들은 현재 미존재. 해당 Phase 시작 시 ADR과 함께 스키마 확정.

- **`portfolio`**: 현재 보유 종목 (Phase 6~7)
- **`order_reservations`**: 예약 주문 (Phase 6). `minervini_list_selection`의 승인 흐름과 통합 설계 필요.
- **`trade_history`**: 체결 기록 (Phase 6)
- **`statistics`**: 매매 통계 집계 (Phase 8)

### B.2 JSON 스키마

#### `conditions_met` (minervini_screen_results_*.conditions_met)

미너비니 8조건 각각의 통과 여부. Phase 1 착수 직전 스크리너 개편으로 도입(ADR-009).

```json
{
  "price_above_ma150_ma200": true,
  "ma150_above_ma200": true,
  "ma200_uptrend_1mo": true,
  "ma50_above_ma150_ma200": true,
  "price_above_ma50": true,
  "price_30pct_above_52w_low": true,
  "price_within_25pct_of_52w_high": true,
  "rs_rating_above_70": true
}
```

8개 키는 미너비니 원전의 트렌드 템플릿 조건에 1:1 대응. 저장 정책이 "통과 종목만 INSERT"이므로 모두 `true`일 수밖에 없으나, **향후 저장 정책 변경 또는 향후 베이스 분석 입력용으로 명시적 구조를 유지**한다.

#### `risk_flags` (daily_analysis_*.risk_flags)

배열. 분석 LLM v2 production lock 기준 (Phase 1.1.15, 2026-05-02). 다음 12개 값만 허용 (`apps/llm-analysis/models/analysis_result.py`의 `VALID_RISK_FLAGS` whitelist와 일치):

- `"climax_run"`: 단기간 급등으로 거래량·변동성 폭증한 climactic 상태
- `"late_stage_base"`: 4번째 이상 베이스 — 통계적으로 실패율 높음
- `"extended_from_ma"`: 50/150/200일 이동평균에서 과도하게 이격 (보통 +10% 이상)
- `"faulty_pivot"`: 베이스 구조에서 식별된 pivot이 잘못 설정됨 (예: ill-defined base, false handle)
- `"low_volume_breakout"`: 돌파 시 거래량이 책 기준(1.4~1.5배 이상) 미달
- `"narrow_base"`: 베이스 진폭이 너무 좁아 institutional accumulation 신호 부족
- `"wide_and_loose"`: 베이스 진폭이 너무 넓고 거칠어 sloppy structure
- `"thin_liquidity_us_only"`: US 개별주에 한해 평균 일일 달러 거래량 < $5M (KR은 평가 안 함)
- `"prior_uptrend_insufficient"`: Stage 2 진입 전 prior uptrend 폭이 25~30% 미만
- `"volume_contraction_on_advance"`: 상승 구간에서 거래량 감소 — institutional 매수 약화 신호
- `"reverse_split_distortion"`: 역분할 등 corporate action으로 차트가 왜곡됨
- `"etf_methodology_mismatch"`: 분석 대상이 ETF 또는 fund vehicle — 미너비니 방법론 직접 적용 불가 (Pre-Check trigger)

예: `["climax_run", "wide_and_loose", "extended_from_ma"]`

**v1(구 taxonomy) 대비 변경 이력**: v1의 `high_rs_rating`, `extended_from_ma50`, `low_volume`, `thin_base`, `earnings_imminent`, `market_weakness`, `sector_overconcentration` 7개는 1.1.15 외부 평가에서 카테고리 에러(특히 `high_rs_rating`은 양성 신호인데 위험으로 분류) 또는 단일 종목 분석으로 판정 불가(market/sector/earnings)로 판명되어 v2에서 제거됐다. 변경 사유는 04_DECISIONS의 v2 production lock 결정 + phase1_progress.md 1.1.15 v2 작성 메모 §"v1 → v2 주요 변경 사항" 참조.

#### `entry_params` (daily_analysis_*.entry_params)

`classification='entry'`일 때만 채워짐. (6) `calculate_entry_params` **v1.1 production lock** 기준 (Phase 1.3.0, commit `c2114f7`, 2026-05-07). `apps/llm-analysis/models/entry_params.py`의 `EntryParams` Pydantic 모델과 일치.

```json
{
  "pivot_price": 22.67,
  "trigger_price": 22.69,
  "current_price": 23.23,
  "stop_loss_price": 21.47,
  "stop_loss_pct_from_pivot": -5.3,
  "stop_loss_pct_from_current_price": -7.6,
  "suggested_weight_pct": 4.9,
  "expected_target_price": 27.20,
  "expected_target_pct": 20.0,
  "entry_window_days": 3,
  "max_chase_pct_from_pivot": 5.0,
  "breakout_volume_requirement": "ge_1.4x_50day_avg",
  "observed_breakout_volume_ratio": 1.02,
  "pattern_basis": "cup_with_handle handle high $22.67",
  "notes": "Position size reduced 0.7x due to low_volume_breakout flag.",
  "known_warnings": [
    "stop_distance_from_current_price_exceeds_book_limit",
    "breakout_volume_below_requirement"
  ],
  "other_warnings": []
}
```

**필드 정의 (16필드)**:

| 필드 | 타입 | 의미 |
|---|---|---|
| `pivot_price` | float | 베이스 돌파 기준선 raw (handle high 또는 base high) |
| `trigger_price` | float | 매수 trigger (default `pivot_price * 1.001`, buffered). v1.1 신규 필드 — (5) reasoning과 (6) 구조 필드 간 ambiguity 제거 |
| `current_price` | float | 분석 시점 종가 (input payload echo). v1.1 신규 필드 — stop_loss_pct_from_current_price 산출용 |
| `stop_loss_price` | float | 손절 가격 |
| `stop_loss_pct_from_pivot` | float | pivot 기준 stop 거리 (%, 음수). 범위 [-10, -5] (사전 자문 §0.6 채택). v1의 `stop_loss_pct`에서 rename. 책 기준 절대 한도 -7~-8% (O'Neil), Minervini 7-8% 룰 또는 risk_flag 기반 tightening |
| `stop_loss_pct_from_current_price` | float | **현 종가 기준** stop 거리 (%, 음수). v1.1 신규 필드. \|값\| > 7.5 시 `stop_distance_from_current_price_exceeds_book_limit` known_warning auto-emit |
| `suggested_weight_pct` | float | 총 자산 대비 진입 비중 (%). 범위 [3, 25]. base 7~20% × risk_flag multipliers |
| `expected_target_price` | float | 1차 목표가 (sell-half 또는 partial exit 기준) |
| `expected_target_pct` | float | pivot 대비 target 거리 (%, 양수) |
| `entry_window_days` | int | 분석 시점부터 buy zone 유효 일수 (보통 3~5거래일) |
| `max_chase_pct_from_pivot` | float | pivot 위로 매수 가능한 최대 거리 (%). O'Neil "5% chase rule" 기반, 보통 5.0 |
| `breakout_volume_requirement` | enum | 돌파 거래량 요건. 값: `"ge_1.3x_50day_avg"` (tight VCP only), `"ge_1.4x_50day_avg"` (default), `"ge_1.5x_50day_avg"` (3c_cheat) |
| `observed_breakout_volume_ratio` | float \| null | LLM이 chart에서 자동 추출한 실제 관측 비율. v1.1 신규 필드. observed < requirement threshold 시 `breakout_volume_below_requirement` known_warning auto-emit |
| `pattern_basis` | enum | 산출 근거가 된 base 패턴. 값: `"flat_base"`, `"cup_with_handle"`, `"vcp"`, `"double_bottom"`, `"3c_cheat"` |
| `notes` | string | 산출 과정의 추가 설명 또는 특이사항 (50~600자) |
| `known_warnings` | array | operational decision 기반 경고 closed-set (Literal enum 12종, 아래 표 참조). v1.1에서 auto-emit 2종 추가 |
| `other_warnings` | array | known_warnings 외 LLM이 자유롭게 식별한 위험 신호 |

**`known_warnings` Literal enum 12종 (v1.1)**:

`apps/llm-analysis/models/entry_params.py`의 `KnownWarning` Literal 타입 + `apps/llm-analysis/prompts/calculate_entry_params_v1_1.md` §8과 1:1 일치.
v1 10종 보존 + v1.1에서 auto-emit 2종 (1·2번) 신규 추가 = 총 12종.

| # | 값 | 발행 경로 | 의미 |
|---|---|---|---|
| 1 | `stop_distance_from_current_price_exceeds_book_limit` | **auto-emit** (Pydantic validator) | `abs(stop_loss_pct_from_current_price) > 7.5` — 현 종가 기준 실현 손실이 O'Neil 7~8% 책 한도 초과 |
| 2 | `breakout_volume_below_requirement` | **auto-emit** (Pydantic validator) | `observed_breakout_volume_ratio`가 `breakout_volume_requirement` threshold(1.3/1.4/1.5) 미달 (size 조정과 무관) |
| 3 | `absolute_stop_used_due_to_wide_handle` | LLM 판단 (operational decision) | absolute stop이 binding — logical stop (final-contraction-low − buffer)이 −10% 이상 악화 |
| 4 | `logical_stop_exceeded_absolute_floor` | LLM 판단 (operational decision) | raw logical stop이 절대 바닥 −10%를 초과하여 −10%로 clamp됨 |
| 5 | `size_floored_due_to_multiple_flags` | LLM 판단 (operational decision) | 누적 multiplier가 최종 비중을 3.0% 최솟값까지 압박 |
| 6 | `size_reduced_due_to_late_stage` | LLM 판단 (operational decision) | `late_stage_base` risk_flag 존재 → 0.7× multiplier 적용 |
| 7 | `size_reduced_due_to_thin_liquidity` | LLM 판단 (operational decision) | `thin_liquidity_us_only` risk_flag 존재 → 0.7× multiplier 적용 |
| 8 | `pattern_basis_inferred_from_data` | LLM 판단 (operational decision) | `prior_analysis.pattern == "none"` + `classification == "entry"` — `flat_base` fallback 사용 |
| 9 | `pattern_refined_to_3c_cheat` | LLM 판단 (operational decision) | `prior_analysis.pattern`이 `cup_with_handle`였으나 `3c_cheat`으로 정밀화 |
| 10 | `extended_from_pivot_already` | LLM 판단 (operational decision) | `current_price > pivot_price * 1.03` — entry_window_days = 1로 단축 |
| 11 | `breakout_volume_requirement_relaxed` | LLM 판단 (operational decision) | `ge_1.3x_50day_avg` 선택 (tight VCP 전용, 완화된 요건) |
| 12 | `stop_buffer_increased_for_shake_protection` | LLM 판단 (operational decision) | logical stop을 visible base low보다 의도적으로 낮게 배치 (round number shakeout 방어) |

**v1.1 production lock 결과 (Phase 1.3.0, 2026-05-07)**:

NVST B.5.5 1차 Evaluator 평가에서 도출된 (6) 함수 표기·투명성 문제 3건을 v1.1로 minor revision 발행. 변경 사항:

| Fix | 항목 | 변경 |
|---|---|---|
| 1 | dual stop_pct 분리 (transparency) | `stop_loss_pct` rename → `stop_loss_pct_from_pivot` + `stop_loss_pct_from_current_price` 둘 다 emit + auto-emit warning |
| 2 | `trigger_price` schema-level 분리 | `pivot_price`(raw) + `trigger_price`(buffered) 둘 다 emit |
| 3 | breakout volume mismatch auto-warning | `observed_breakout_volume_ratio` 신규 emit + auto-emit warning |

**검증**: 단위 테스트 53/53 통과 (test_entry_params 53건, v1.1 신규 14건). NVST 합성 검증 6/6 OK (auto-emit 2종 모두 trigger).

**산출물**:
- `apps/llm-analysis/prompts/calculate_entry_params_v1_1.md` (v1 보존)
- `apps/llm-analysis/models/entry_params.py` 갱신 (auto-emit validator)
- `apps/llm-analysis/core/result_parser.py` 갱신 (v1 → v1.1 legacy 매핑)
- `apps/llm-analysis/config/settings.yaml`: `prompts.calculate_entry_params: v1` → `v1_1`

**구 스키마와의 차이**:
- brief v0 (7필드) → v1 (13필드) → v1.1 (16필드)
- v0 → v1: phase1_progress.md 1.2 트랙 B B.1 사전 자문 메모 + commit `dd09e2d` 참조
- v1 → v1.1: phase1_progress.md 1.3.0 메모 + commit `c2114f7` 참조

### B.3 모듈 함수 시그니처

#### Phase 1 (5) 차트 분석

```python
def analyze_chart(symbol: str, date: date, market: str) -> AnalysisResult:
    """
    템플릿 통과 종목 1개에 대해 차트 분석을 수행한다.
    
    Args:
        symbol: 종목 코드 (예: '005930', 'AAPL')
        date: 분석 기준일
        market: 'KOSPI' | 'KOSDAQ' | 'ETF' | 'NYSE' | 'NASDAQ'
                (region은 market에서 유도)
    
    Returns:
        AnalysisResult (Pydantic 모델, daily_analysis_{region} 스키마와 일치)
    
    Side effects:
        - llm_calls 테이블에 호출 로그 기록
        - daily_analysis_kr 또는 daily_analysis_us 테이블에 결과 저장
    """
```

#### Phase 1 (6) 진입 파라미터

```python
def calculate_entry_params(symbol: str, date: date, market: str,
                           prior_analysis: AnalysisResult) -> EntryParams:
    """
    (5)에서 entry로 분류된 종목에 대해 진입 파라미터를 산출한다.
    
    Args:
        symbol, date, market: 분석 대상
        prior_analysis: (5)의 결과
    
    Returns:
        EntryParams (entry_params JSON 스키마와 일치)
    """
```

#### Phase 4 (8) Q&A 에이전트 도구

```python
# 모든 도구는 읽기 전용. SELECT 외 작업 금지.

def get_stock_data(symbol: str, market: str, period_days: int) -> dict
def get_analysis_history(symbol: str, market: str, days: int) -> list[dict]
def search_similar_patterns(symbol: str, market: str, criteria: dict) -> list[dict]
def get_indicator(symbol: str, market: str, indicator_name: str, days: int) -> dict
```

#### Phase 7 (11) 포트폴리오 매니저 도구

```python
def get_portfolio_snapshot() -> dict
def calculate_sector_exposure() -> dict
def get_trade_history(days: int) -> list[dict]
def calculate_risk_metrics() -> dict
```

---

## Part C: 외부 API 인터페이스

### Anthropic LLM 백엔드

본 시스템은 두 가지 백엔드를 추상화 인터페이스(`LLMBackend`) 뒤에 둔다.
런타임에 `apps/llm-analysis/config/settings.yaml`의 `llm_analysis.backend` 값으로 선택.

| 백엔드 | 용도 | 활성 시점 |
|---|---|---|
| `cli` | Claude Code CLI + Max 플랜 | Phase 1 기본 (ADR-011) |
| `api` | Anthropic API | ADR-011 전환 시점 또는 자동화 Phase |

공통 설정:
- temperature: 0 (분석 모듈), 0.7 (Q&A 에이전트)
- 출력 강제: tool use / JSON mode (API), 프롬프트 강제 (CLI)
- 모든 호출은 `llm_calls` 테이블에 기록 (헌법 §2.5)


### 증권사 API
- **선정**: Phase 6 진입 시 결정 (별도 ADR로 기록)
- **모드**: 페이퍼 트레이딩 → 실거래

### SMTP
- **호스트**: smtp.gmail.com
- **인증**: 앱 비밀번호 (환경변수 관리)

### 외부 데이터 소스 (Phase 0에서 이미 사용 중)
- **pykrx**: KR 주식·지수 일봉
- **FDR (FinanceDataReader)**: US 주식·지수 일봉, KR 섹터 정보
- **yfinance**: US 데이터 보조
- **Binance API**: 크립토 일봉

---

## Part D: 환경 변수 규약

```
# .env 파일 (.gitignore에 포함)
ANTHROPIC_API_KEY=...
DB_HOST=localhost
DB_PORT=3306
DB_USER=...
DB_PASSWORD=...
DB_NAME=market
SMTP_USER=...
SMTP_APP_PASSWORD=...
NOTIFY_EMAIL=...
BROKER_API_KEY=...        # Phase 6에서 추가
BROKER_API_SECRET=...     # Phase 6에서 추가
PAPER_TRADING_MODE=true   # Phase 6에서 사용
```

---

*이 문서는 모듈 간 약속의 모음이다. 약속이 깨지면 시스템이 깨진다. 변경은 신중히, 추적은 철저히.*