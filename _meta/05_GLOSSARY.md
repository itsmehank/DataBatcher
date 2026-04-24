# 용어집 및 인터페이스 정의

> 이 문서는 프로젝트에서 사용하는 용어와 모듈 간 인터페이스(데이터 스키마)를 정의한다.  
> **모듈 간 유기적 연결의 핵심이 되는 문서**이다. 새 모듈을 만들 때 반드시 이 문서를 참조한다.  
> 인터페이스 변경 시 ADR을 작성하고, 영향받는 모듈 목록을 명시한다.

---

## Part A: 도메인 용어

### 미너비니 트레이딩 용어

**미너비니 템플릿 (Trend Template)**: Mark Minervini가 정의한 8가지 조건. 강한 상승 추세에 있는 종목을 필터링하기 위한 규칙.

**RS Rating (Relative Strength Rating)**: 종목의 가격 모멘텀을 시장 전체 종목 대비 백분위로 표시 (1~99). IBD에서 사용.

**RS Line**: 종목 가격을 벤치마크(보통 S&P 500)로 나눈 비율의 시계열. 우상향이면 시장 대비 강세.

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

---

## Part B: 데이터 스키마

### B.1 DB 테이블 스키마

#### `daily_ohlcv`
종목별 일봉 데이터. (1)이 적재.

```sql
CREATE TABLE daily_ohlcv (
    ticker      VARCHAR(20) NOT NULL,
    date        DATE NOT NULL,
    open        DECIMAL(15,4),
    high        DECIMAL(15,4),
    low         DECIMAL(15,4),
    close       DECIMAL(15,4),
    volume      BIGINT,
    market      VARCHAR(20),  -- 'KOSPI' | 'KOSDAQ' | 'NYSE' | 'NASDAQ'
    PRIMARY KEY (ticker, date),
    INDEX idx_date (date)
);
```

#### `daily_indicators`
종목별 인디케이터. (2)가 적재.

```sql
CREATE TABLE daily_indicators (
    ticker      VARCHAR(20) NOT NULL,
    date        DATE NOT NULL,
    sma50       DECIMAL(15,4),
    sma100      DECIMAL(15,4),
    sma150      DECIMAL(15,4),
    sma200      DECIMAL(15,4),
    rs_line     DECIMAL(20,8),
    rs_rating   INT,           -- 1~99
    volume_ma20 BIGINT,
    high_52w    DECIMAL(15,4),
    low_52w     DECIMAL(15,4),
    PRIMARY KEY (ticker, date)
);
```

#### `template_pass`
미너비니 템플릿 통과 종목. (3)이 적재.

```sql
CREATE TABLE template_pass (
    ticker          VARCHAR(20) NOT NULL,
    date            DATE NOT NULL,
    conditions_met  JSON,       -- 8개 조건 각각의 통과 여부
    PRIMARY KEY (ticker, date)
);
```

#### `daily_analysis` ⭐
LLM 분석 결과. (5)(6)이 적재. **이 스키마는 Phase 1의 핵심 산출물.**

```sql
CREATE TABLE daily_analysis (
    ticker          VARCHAR(20) NOT NULL,
    date            DATE NOT NULL,
    classification  VARCHAR(20) NOT NULL,  -- 'entry' | 'watch' | 'ignore'
    confidence      DECIMAL(3,2),          -- 0.00 ~ 1.00
    reasoning       TEXT,                  -- 자연어 근거
    pattern         VARCHAR(50),           -- 'VCP' | 'flat_base' | 'cup_handle' | 'none' 등
    risk_flags      JSON,                  -- ['high_rs_rating', 'low_volume', ...]
    entry_params    JSON,                  -- 아래 B.2 참조 (entry 분류 시에만)
    llm_call_id     BIGINT,                -- llm_calls 테이블 외래키
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ticker, date),
    INDEX idx_date_class (date, classification)
);
```

#### `portfolio`
현재 보유 종목. (10)이 갱신.

```sql
CREATE TABLE portfolio (
    ticker          VARCHAR(20) PRIMARY KEY,
    quantity        INT NOT NULL,
    avg_entry_price DECIMAL(15,4),
    current_price   DECIMAL(15,4),
    entry_date      DATE,
    stop_loss_price DECIMAL(15,4),
    sector          VARCHAR(50),
    weight_pct      DECIMAL(5,2),    -- 총자산 대비 비중
    last_updated    TIMESTAMP
);
```

#### `order_reservations`
사용자가 승인한 예약 주문. (9)가 감시.

```sql
CREATE TABLE order_reservations (
    id              BIGINT PRIMARY KEY AUTO_INCREMENT,
    ticker          VARCHAR(20) NOT NULL,
    order_type      VARCHAR(20),     -- 'entry' | 'exit' | 'stop_loss'
    trigger_price   DECIMAL(15,4),
    trigger_volume_ratio DECIMAL(5,2), -- 거래량 평균 대비 (entry 시)
    quantity        INT,
    weight_pct      DECIMAL(5,2),
    expires_at      DATE,
    status          VARCHAR(20),     -- 'active' | 'triggered' | 'expired' | 'cancelled'
    created_at      TIMESTAMP,
    triggered_at    TIMESTAMP,
    related_analysis_id BIGINT      -- daily_analysis 참조
);
```

#### `trade_history`
체결된 매매. (10)이 적재.

```sql
CREATE TABLE trade_history (
    id              BIGINT PRIMARY KEY AUTO_INCREMENT,
    ticker          VARCHAR(20) NOT NULL,
    side            VARCHAR(10),     -- 'buy' | 'sell'
    quantity        INT,
    price           DECIMAL(15,4),
    timestamp       TIMESTAMP,
    reservation_id  BIGINT,          -- order_reservations 참조
    pnl             DECIMAL(15,4),   -- 매도 시에만
    pnl_pct         DECIMAL(7,4),    -- 매도 시에만
    holding_days    INT              -- 매도 시에만
);
```

#### `llm_calls`
모든 LLM 호출 로그. 헌법 §2.5에 의한 필수 기록.

```sql
CREATE TABLE llm_calls (
    id              BIGINT PRIMARY KEY AUTO_INCREMENT,
    timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    module          VARCHAR(50),     -- 'analysis_5' | 'analysis_6' | 'agent_8' | 'agent_11'
    model           VARCHAR(50),
    prompt_tokens   INT,
    completion_tokens INT,
    cost_usd        DECIMAL(10,6),
    request_payload JSON,
    response_payload JSON,
    duration_ms     INT,
    error           TEXT NULL
);
```

#### `statistics`
매매 통계 집계. (12)가 적재.

```sql
CREATE TABLE statistics (
    period_start    DATE,
    period_end      DATE,
    period_type     VARCHAR(20),     -- 'daily' | 'weekly' | 'monthly' | 'cumulative'
    win_rate        DECIMAL(5,2),
    avg_win_pct     DECIMAL(7,4),
    avg_loss_pct    DECIMAL(7,4),
    expectancy_r    DECIMAL(7,4),    -- R-multiple 기준 기대값
    max_drawdown    DECIMAL(7,4),
    trade_count     INT,
    extra_metrics   JSON,
    PRIMARY KEY (period_start, period_end, period_type)
);
```

### B.2 JSON 스키마

#### `entry_params` (daily_analysis 테이블의 JSON 필드)

```json
{
  "pivot_price": 165.00,
  "stop_loss_price": 152.00,
  "stop_loss_pct": -7.88,
  "suggested_weight_pct": 15.0,
  "volume_confirmation": {
    "required": true,
    "ratio_to_ma20": 1.5
  },
  "expected_target": {
    "conservative": 180.00,
    "optimistic": 210.00
  },
  "valid_until": "2026-04-28"
}
```

#### `risk_flags` (daily_analysis 테이블의 JSON 필드)

가능한 플래그 값:
- `"high_rs_rating"`: RS Rating 95 이상
- `"extended_from_ma50"`: 50일 이평선에서 너무 멀리 이격
- `"low_volume"`: 거래량 부족
- `"thin_base"`: 베이스 기간이 너무 짧음 (<7주)
- `"sector_overconcentration"`: 해당 섹터에 이미 충분한 노출
- `"earnings_imminent"`: 실적 발표 임박
- `"market_weakness"`: 전체 시장이 약세 국면

#### `conditions_met` (template_pass 테이블의 JSON 필드)

미너비니 8조건 각각:

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

### B.3 모듈 함수 시그니처

#### Phase 1 (5) 차트 분석

```python
def analyze_chart(ticker: str, date: date) -> AnalysisResult:
    """
    템플릿 통과 종목 1개에 대해 차트 분석을 수행한다.
    
    Args:
        ticker: 종목 코드
        date: 분석 기준일
    
    Returns:
        AnalysisResult (Pydantic 모델, daily_analysis 테이블 스키마와 일치)
    
    Side effects:
        - llm_calls 테이블에 호출 로그 기록
        - daily_analysis 테이블에 결과 저장
    """
```

#### Phase 1 (6) 진입 파라미터

```python
def calculate_entry_params(ticker: str, date: date, 
                           prior_analysis: AnalysisResult) -> EntryParams:
    """
    (5)에서 entry로 분류된 종목에 대해 진입 파라미터를 산출한다.
    
    Args:
        ticker, date: 분석 대상
        prior_analysis: (5)의 결과
    
    Returns:
        EntryParams (entry_params JSON 스키마와 일치)
    """
```

#### Phase 4 (8) Q&A 에이전트 도구

```python
# 모든 도구는 읽기 전용. SELECT 외 작업 금지.

def get_stock_data(ticker: str, period_days: int) -> dict
def get_analysis_history(ticker: str, days: int) -> list[dict]
def search_similar_patterns(ticker: str, criteria: dict) -> list[dict]
def get_indicator(ticker: str, indicator_name: str, days: int) -> dict
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

### Anthropic API
- **모델**: 사용 시점의 최신 Sonnet 또는 Opus
- **temperature**: 0 (분석 모듈), 0.7 (Q&A 에이전트)
- **출력 강제**: tool use 또는 JSON mode

### 증권사 API
- **선정**: Phase 6 진입 시 결정 (별도 ADR로 기록)
- **모드**: 페이퍼 트레이딩 → 실거래

### SMTP
- **호스트**: smtp.gmail.com
- **인증**: 앱 비밀번호 (환경변수 관리)

---

## Part D: 환경 변수 규약

```
# .env 파일 (.gitignore에 포함)
ANTHROPIC_API_KEY=...
DB_HOST=localhost
DB_PORT=3306
DB_USER=...
DB_PASSWORD=...
DB_NAME=minervini
SMTP_USER=...
SMTP_APP_PASSWORD=...
NOTIFY_EMAIL=...
BROKER_API_KEY=...        # Phase 6에서 추가
BROKER_API_SECRET=...     # Phase 6에서 추가
PAPER_TRADING_MODE=true   # Phase 6에서 사용
```

---

*이 문서는 모듈 간 약속의 모음이다. 약속이 깨지면 시스템이 깨진다. 변경은 신중히, 추적은 철저히.*
