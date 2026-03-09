-- Initial schema for DataBatcher (applied automatically by docker-entrypoint)

-- Prices: Stocks
CREATE TABLE IF NOT EXISTS stock_prices (
  symbol        VARCHAR(32)  NOT NULL,
  date          DATE         NOT NULL,
  open          DECIMAL(18,4),
  high          DECIMAL(18,4),
  low           DECIMAL(18,4),
  close         DECIMAL(18,4),            -- 원시 종가(수정 전)
  adj_close     DECIMAL(18,4) NULL,       -- 수정 종가
  volume        BIGINT,
  market        VARCHAR(16) NOT NULL,     -- 상장 시장 구분: KOSPI/KOSDAQ/KONEX (레거시: XKRX 등으로 쓰였던 적 있음)
  source        VARCHAR(16) NOT NULL,     -- pykrx 등
  etl_loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (symbol, date),
  KEY idx_date (date),
  KEY idx_market_date (market, date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================
-- Crypto Tables (Binance Spot, USDT, Daily)
-- ============================================

-- Crypto symbol master (Binance trading pairs)
CREATE TABLE IF NOT EXISTS crypto_symbol_master (
  symbol        VARCHAR(32)  NOT NULL,     -- e.g., BTCUSDT
  base_asset    VARCHAR(16)  NOT NULL,     -- e.g., BTC
  quote_asset   VARCHAR(16)  NOT NULL,     -- e.g., USDT
  status        VARCHAR(16)  NOT NULL,     -- ACTIVE/INACTIVE
  exchange      VARCHAR(16)  NOT NULL,     -- BINANCE
  etl_loaded_at TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (symbol),
  KEY idx_quote_status (quote_asset, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Daily prices (UTC date)
CREATE TABLE IF NOT EXISTS crypto_prices_daily (
  symbol        VARCHAR(32)  NOT NULL,
  date          DATE         NOT NULL,     -- UTC date
  open          DECIMAL(28,10) NULL,
  high          DECIMAL(28,10) NULL,
  low           DECIMAL(28,10) NULL,
  close         DECIMAL(28,10) NULL,
  volume_quote  DECIMAL(28,10) NULL,      -- quoteAssetVolume (USDT)
  exchange      VARCHAR(16)  NOT NULL,     -- BINANCE
  source        VARCHAR(16)  NOT NULL,     -- binance
  etl_loaded_at TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (symbol, date),
  KEY idx_date (date),
  KEY idx_symbol_date (symbol, date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Daily indicators (long form)
CREATE TABLE IF NOT EXISTS crypto_indicators_daily (
  symbol        VARCHAR(32) NOT NULL,
  date          DATE        NOT NULL,
  indicator     VARCHAR(64) NOT NULL,
  params_hash   CHAR(40)    NOT NULL,
  value         DECIMAL(28,10) NULL,
  exchange      VARCHAR(16) NOT NULL,     -- BINANCE
  source        VARCHAR(16) NOT NULL,     -- binance
  etl_loaded_at TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (symbol, date, indicator, params_hash),
  KEY idx_indicator_date (indicator, date),
  KEY idx_symbol_date (symbol, date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================
-- Crypto Tables (Binance Spot, USDT, Weekly)
-- ============================================

CREATE TABLE IF NOT EXISTS crypto_prices_weekly (
  symbol        VARCHAR(32)  NOT NULL,
  week_start    DATE         NOT NULL,     -- UTC Monday
  week_end      DATE         NOT NULL,     -- UTC Sunday
  open          DECIMAL(28,10) NULL,
  high          DECIMAL(28,10) NULL,
  low           DECIMAL(28,10) NULL,
  close         DECIMAL(28,10) NULL,
  volume_quote  DECIMAL(28,10) NULL,      -- quoteAssetVolume (USDT)
  exchange      VARCHAR(16)  NOT NULL,     -- BINANCE
  source        VARCHAR(16)  NOT NULL,     -- binance
  etl_loaded_at TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (symbol, week_start),
  KEY idx_week_start (week_start),
  KEY idx_symbol_week (symbol, week_start)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS crypto_indicators_weekly (
  symbol        VARCHAR(32) NOT NULL,
  week_start    DATE        NOT NULL,
  indicator     VARCHAR(64) NOT NULL,
  params_hash   CHAR(40)    NOT NULL,
  value         DECIMAL(28,10) NULL,
  exchange      VARCHAR(16) NOT NULL,     -- BINANCE
  source        VARCHAR(16) NOT NULL,     -- binance
  etl_loaded_at TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (symbol, week_start, indicator, params_hash),
  KEY idx_indicator_week (indicator, week_start),
  KEY idx_symbol_week (symbol, week_start)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Indicators (long form)
CREATE TABLE IF NOT EXISTS stock_indicators (
  symbol        VARCHAR(32) NOT NULL,
  date          DATE        NOT NULL,
  indicator     VARCHAR(64) NOT NULL,     -- 예: sma, rsi, macd_signal
  params_hash   CHAR(40)    NOT NULL,     -- 파라미터 해시(sha1 등)
  value         DECIMAL(28,10) NULL,
  market        VARCHAR(16) NOT NULL,     -- 상장 시장 구분: KOSPI/KOSDAQ/KONEX
  source        VARCHAR(16) NOT NULL,     -- 파생 원천(FDR)
  etl_loaded_at TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (symbol, date, indicator, params_hash),
  KEY idx_indicator_date (indicator, date),
  KEY idx_symbol_date (symbol, date),
  KEY idx_indicator_date_market_symbol (indicator, date, market, symbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Symbol master
CREATE TABLE IF NOT EXISTS symbol_master (
  symbol        VARCHAR(32) PRIMARY KEY,
  market        VARCHAR(16) NOT NULL,      -- 상장 시장 구분: KOSPI/KOSDAQ/KONEX/ETF
  symbol_type   VARCHAR(16) NULL,          -- STOCK / ETF
  name          VARCHAR(128) NULL,
  status        VARCHAR(16) NOT NULL,      -- ACTIVE/DELISTED/IPO_PENDING
  sector        VARCHAR(128) NULL,         -- pykrx 대분류 (26개)
  sector_detail VARCHAR(256) NULL,         -- FDR KRX-DESC 세분류 (162개)
  industry      VARCHAR(512) NULL,         -- FDR KRX-DESC Industry
  sector_source VARCHAR(32) NULL,          -- pykrx+fdr / pykrx / fdr / yfinance
  sector_updated_at TIMESTAMP NULL,
  first_date    DATE NULL,
  last_date     DATE NULL,
  updated_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_market_status_sector_name (market, status, sector, name),
  KEY idx_market_status_sector_symbol (market, status, sector, symbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Sync/Health log
CREATE TABLE IF NOT EXISTS sync_log (
  id            BIGINT AUTO_INCREMENT PRIMARY KEY,
  job_name      VARCHAR(64) NOT NULL,      -- daily_update, gap_filler, resync 등
  market        VARCHAR(16) NOT NULL,
  symbol        VARCHAR(32) NULL,
  start_time    DATETIME NOT NULL,
  end_time      DATETIME NULL,
  rows_processed INT DEFAULT 0,
  status        VARCHAR(16) NOT NULL,      -- SUCCESS/FAIL/PARTIAL
  message       VARCHAR(1024) NULL,
  created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_job_market_time (job_name, market, start_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================
-- Weekly Tables
-- ============================================

-- Prices: Stocks (Weekly)
CREATE TABLE IF NOT EXISTS stock_prices_weekly (
  symbol        VARCHAR(32)  NOT NULL,
  week_start    DATE         NOT NULL,     -- 주의 시작일 (yyyy-mm-dd)
  week_end      DATE         NOT NULL,     -- 주의 종료일 (yyyy-mm-dd)
  open          DECIMAL(18,4),
  high          DECIMAL(18,4),
  low           DECIMAL(18,4),
  close         DECIMAL(18,4),
  adj_close     DECIMAL(18,4) NULL,
  volume        BIGINT,
  market        VARCHAR(16) NOT NULL,     -- 상장 시장 구분: KOSPI/KOSDAQ/KONEX
  source        VARCHAR(16) NOT NULL,
  etl_loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (symbol, week_start),
  KEY idx_week_start (week_start),
  KEY idx_market_week (market, week_start)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Indicators: Stocks (Weekly, long form)
CREATE TABLE IF NOT EXISTS stock_indicators_weekly (
  symbol        VARCHAR(32) NOT NULL,
  week_start    DATE        NOT NULL,      -- 주의 시작일 (yyyy-mm-dd)
  indicator     VARCHAR(64) NOT NULL,
  params_hash   CHAR(40)    NOT NULL,
  value         DECIMAL(28,10) NULL,
  market        VARCHAR(16) NOT NULL,     -- 상장 시장 구분: KOSPI/KOSDAQ/KONEX
  source        VARCHAR(16) NOT NULL,
  etl_loaded_at TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (symbol, week_start, indicator, params_hash),
  KEY idx_indicator_week (indicator, week_start),
  KEY idx_symbol_week (symbol, week_start)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================
-- US Stock Tables (NYSE, NASDAQ, ETF - Daily)
-- ============================================

-- US Symbol master
CREATE TABLE IF NOT EXISTS us_symbol_master (
  symbol        VARCHAR(32) PRIMARY KEY,       -- e.g., AAPL, MSFT
  market        VARCHAR(16) NOT NULL,          -- NYSE / NASDAQ / ETF
  symbol_type   VARCHAR(16) NULL,              -- STOCK / ETF
  name          VARCHAR(256) NULL,             -- Company name
  status        VARCHAR(16) NOT NULL,          -- ACTIVE / DELISTED
  sector        VARCHAR(128) NULL,             -- Sector (yfinance)
  industry      VARCHAR(128) NULL,             -- Industry (FDR / yfinance)
  sector_source VARCHAR(32) NULL,              -- fdr / yfinance / fdr+yfinance
  sector_updated_at TIMESTAMP NULL,
  etl_loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- US Daily prices
CREATE TABLE IF NOT EXISTS us_stock_prices (
  symbol        VARCHAR(32)  NOT NULL,
  date          DATE         NOT NULL,
  open          DECIMAL(18,4),
  high          DECIMAL(18,4),
  low           DECIMAL(18,4),
  close         DECIMAL(18,4),
  adj_close     DECIMAL(18,4) NULL,
  volume        BIGINT,
  market        VARCHAR(16) NOT NULL,          -- NYSE / NASDAQ / ETF
  source        VARCHAR(16) NOT NULL,          -- fdr
  etl_loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (symbol, date),
  KEY idx_date (date),
  KEY idx_market_date (market, date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- US Daily indicators (long form)
CREATE TABLE IF NOT EXISTS us_stock_indicators (
  symbol        VARCHAR(32) NOT NULL,
  date          DATE        NOT NULL,
  indicator     VARCHAR(64) NOT NULL,
  params_hash   CHAR(40)    NOT NULL,
  value         DECIMAL(28,10) NULL,
  market        VARCHAR(16) NOT NULL,
  source        VARCHAR(16) NOT NULL,
  etl_loaded_at TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (symbol, date, indicator, params_hash),
  KEY idx_indicator_date (indicator, date),
  KEY idx_symbol_date (symbol, date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- US Weekly prices
CREATE TABLE IF NOT EXISTS us_stock_prices_weekly (
  symbol        VARCHAR(32)  NOT NULL,
  week_start    DATE         NOT NULL,     -- Week start date (Monday)
  week_end      DATE         NOT NULL,     -- Week end date (Friday)
  open          DECIMAL(18,4),
  high          DECIMAL(18,4),
  low           DECIMAL(18,4),
  close         DECIMAL(18,4),
  adj_close     DECIMAL(18,4) NULL,
  volume        BIGINT,
  market        VARCHAR(16) NOT NULL,      -- NYSE / NASDAQ / ETF
  source        VARCHAR(16) NOT NULL,      -- fdr
  etl_loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (symbol, week_start),
  KEY idx_week_start (week_start),
  KEY idx_market_week (market, week_start)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- US Weekly indicators (long form)
CREATE TABLE IF NOT EXISTS us_stock_indicators_weekly (
  symbol        VARCHAR(32) NOT NULL,
  week_start    DATE        NOT NULL,
  indicator     VARCHAR(64) NOT NULL,
  params_hash   CHAR(40)    NOT NULL,
  value         DECIMAL(28,10) NULL,
  market        VARCHAR(16) NOT NULL,
  source        VARCHAR(16) NOT NULL,
  etl_loaded_at TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (symbol, week_start, indicator, params_hash),
  KEY idx_indicator_week (indicator, week_start),
  KEY idx_symbol_week (symbol, week_start)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================
-- KR Index Tables (KOSPI/KOSDAQ Index - Daily)
-- ============================================

-- KR Index master (KOSPI 1001, KOSDAQ 2001)
CREATE TABLE IF NOT EXISTS kr_index_master (
  symbol        VARCHAR(32) PRIMARY KEY,        -- '1001', '2001'
  market        VARCHAR(16) NOT NULL,           -- KOSPI / KOSDAQ
  name          VARCHAR(128) NULL,              -- '코스피', '코스닥'
  status        VARCHAR(16) NOT NULL DEFAULT 'ACTIVE',
  etl_loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- KR Index daily prices (no adj_close - index doesn't need adjusted price)
CREATE TABLE IF NOT EXISTS kr_index_prices (
  symbol        VARCHAR(32)  NOT NULL,
  date          DATE         NOT NULL,
  open          DECIMAL(18,4),
  high          DECIMAL(18,4),
  low           DECIMAL(18,4),
  close         DECIMAL(18,4),
  volume        BIGINT,
  market        VARCHAR(16) NOT NULL,           -- KOSPI / KOSDAQ
  source        VARCHAR(16) NOT NULL,           -- pykrx
  etl_loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (symbol, date),
  KEY idx_date (date),
  KEY idx_market_date (market, date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- KR Index daily indicators (long form)
CREATE TABLE IF NOT EXISTS kr_index_indicators (
  symbol        VARCHAR(32) NOT NULL,
  date          DATE        NOT NULL,
  indicator     VARCHAR(64) NOT NULL,
  params_hash   CHAR(40)    NOT NULL,
  value         DECIMAL(28,10) NULL,
  market        VARCHAR(16) NOT NULL,
  source        VARCHAR(16) NOT NULL,
  etl_loaded_at TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (symbol, date, indicator, params_hash),
  KEY idx_indicator_date (indicator, date),
  KEY idx_symbol_date (symbol, date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================
-- KR Index Weekly Tables (KOSPI/KOSDAQ Index - Weekly)
-- ============================================

-- KR Index weekly prices (no adj_close - index doesn't need adjusted price)
CREATE TABLE IF NOT EXISTS kr_index_prices_weekly (
  symbol        VARCHAR(32)  NOT NULL,
  week_start    DATE         NOT NULL,
  week_end      DATE         NOT NULL,
  open          DECIMAL(18,4),
  high          DECIMAL(18,4),
  low           DECIMAL(18,4),
  close         DECIMAL(18,4),
  volume        BIGINT,
  market        VARCHAR(16) NOT NULL,       -- KOSPI / KOSDAQ
  source        VARCHAR(16) NOT NULL,       -- pykrx
  etl_loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (symbol, week_start),
  KEY idx_week_start (week_start),
  KEY idx_market_week (market, week_start)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- KR Index weekly indicators (long form)
CREATE TABLE IF NOT EXISTS kr_index_indicators_weekly (
  symbol        VARCHAR(32) NOT NULL,
  week_start    DATE        NOT NULL,
  indicator     VARCHAR(64) NOT NULL,
  params_hash   CHAR(40)    NOT NULL,
  value         DECIMAL(28,10) NULL,
  market        VARCHAR(16) NOT NULL,
  source        VARCHAR(16) NOT NULL,
  etl_loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (symbol, week_start, indicator, params_hash),
  KEY idx_indicator_week (indicator, week_start),
  KEY idx_symbol_week (symbol, week_start)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================
-- US Index Tables (S&P 500, DJI, IXIC - Daily)
-- ============================================

-- US Index master (US500, DJI, IXIC)
CREATE TABLE IF NOT EXISTS us_index_master (
  symbol        VARCHAR(32) PRIMARY KEY,        -- 'US500', 'DJI', 'IXIC'
  market        VARCHAR(16) NOT NULL,           -- SP500 / DJI / IXIC
  name          VARCHAR(128) NULL,              -- 'S&P 500', 'Dow Jones Industrial Average', ...
  status        VARCHAR(16) NOT NULL DEFAULT 'ACTIVE',
  etl_loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- US Index daily prices (no adj_close - index doesn't need adjusted price)
CREATE TABLE IF NOT EXISTS us_index_prices (
  symbol        VARCHAR(32)  NOT NULL,
  date          DATE         NOT NULL,
  open          DECIMAL(18,4),
  high          DECIMAL(18,4),
  low           DECIMAL(18,4),
  close         DECIMAL(18,4),
  volume        BIGINT,
  market        VARCHAR(16) NOT NULL,           -- SP500 / DJI / IXIC
  source        VARCHAR(16) NOT NULL,           -- fdr
  etl_loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (symbol, date),
  KEY idx_date (date),
  KEY idx_market_date (market, date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- US Index daily indicators (long form)
CREATE TABLE IF NOT EXISTS us_index_indicators (
  symbol        VARCHAR(32) NOT NULL,
  date          DATE        NOT NULL,
  indicator     VARCHAR(64) NOT NULL,
  params_hash   CHAR(40)    NOT NULL,
  value         DECIMAL(28,10) NULL,
  market        VARCHAR(16) NOT NULL,
  source        VARCHAR(16) NOT NULL,
  etl_loaded_at TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (symbol, date, indicator, params_hash),
  KEY idx_indicator_date (indicator, date),
  KEY idx_symbol_date (symbol, date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================
-- US Index Tables (S&P 500, DJI, IXIC - Weekly)
-- ============================================

-- US Index Weekly prices (no adj_close - index doesn't need adjusted price)
CREATE TABLE IF NOT EXISTS us_index_prices_weekly (
  symbol        VARCHAR(32)  NOT NULL,
  week_start    DATE         NOT NULL,     -- Week start date (first trading day)
  week_end      DATE         NOT NULL,     -- Week end date (last trading day)
  open          DECIMAL(18,4),
  high          DECIMAL(18,4),
  low           DECIMAL(18,4),
  close         DECIMAL(18,4),
  volume        BIGINT,
  market        VARCHAR(16) NOT NULL,      -- SP500 / DJI / IXIC
  source        VARCHAR(16) NOT NULL,      -- fdr
  etl_loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (symbol, week_start),
  KEY idx_week_start (week_start),
  KEY idx_market_week (market, week_start)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- US Index Weekly indicators (long form)
CREATE TABLE IF NOT EXISTS us_index_indicators_weekly (
  symbol        VARCHAR(32) NOT NULL,
  week_start    DATE        NOT NULL,
  indicator     VARCHAR(64) NOT NULL,
  params_hash   CHAR(40)    NOT NULL,
  value         DECIMAL(28,10) NULL,
  market        VARCHAR(16) NOT NULL,
  source        VARCHAR(16) NOT NULL,
  etl_loaded_at TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (symbol, week_start, indicator, params_hash),
  KEY idx_indicator_week (indicator, week_start),
  KEY idx_symbol_week (symbol, week_start)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


CREATE TABLE IF NOT EXISTS watchlist_items (
  id           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id      BIGINT UNSIGNED NOT NULL,         -- Grafana ${__user.id}
  user_login   VARCHAR(190) NULL,                -- Grafana ${__user.login} (표시용)
  market       VARCHAR(8) NOT NULL,              -- 'KR' / 'US'
  symbol       VARCHAR(32) NOT NULL,
  group_type   ENUM('BUY_ALERT','HIGH_ON_DECK','WATCHLIST','DISCARD') NOT NULL,
  note         TEXT NULL,
  created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_user_market_symbol (user_id, market, symbol),
  KEY idx_market_group (market, group_type, updated_at),
  KEY idx_symbol (market, symbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS minervini_list_selection (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  region VARCHAR(8) NOT NULL COMMENT 'KR | US',
  `date` DATE NOT NULL,
  market VARCHAR(32) NOT NULL,
  symbol VARCHAR(32) NOT NULL,
  list_type VARCHAR(16) NOT NULL COMMENT 'focus | action | pass',
  trigger_price DECIMAL(18,4) NULL,
  stop_price DECIMAL(18,4) NULL,
  status_tag VARCHAR(32) NULL,
  memo TEXT NULL,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_minervini_list_selection (region, `date`, market, symbol),
  KEY idx_minervini_list_selection_lookup (region, `date`, list_type),
  CONSTRAINT chk_minervini_list_type
    CHECK (list_type IN ('focus', 'action', 'pass')),
  CONSTRAINT chk_trigger_price_nonneg
    CHECK (trigger_price IS NULL OR trigger_price >= 0),
  CONSTRAINT chk_stop_price_nonneg
    CHECK (stop_price IS NULL OR stop_price >= 0)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_0900_ai_ci;


-- ============================================
-- Views
-- ============================================

-- 주가와 주요 이동평균선을 결합한 뷰
CREATE OR REPLACE VIEW v_stock_price_with_ma AS
SELECT
  p.symbol,
  p.date,
  p.open,
  p.high,
  p.low,
  p.adj_close AS close,
  p.volume,

  MAX(CASE WHEN i.indicator = 'sma_50_close'  THEN i.value END) AS sma_50,
  MAX(CASE WHEN i.indicator = 'sma_100_close' THEN i.value END) AS sma_100,
  MAX(CASE WHEN i.indicator = 'sma_150_close' THEN i.value END) AS sma_150,
  MAX(CASE WHEN i.indicator = 'sma_200_close' THEN i.value END) AS sma_200,
  MAX(CASE WHEN i.indicator = 'rs_line'       THEN i.value END) AS rs_line

FROM stock_prices p
LEFT JOIN stock_indicators i
  ON p.symbol = i.symbol
 AND p.date   = i.date

GROUP BY
  p.symbol, p.date, p.open, p.high, p.low, p.close, p.volume;

-- 주봉 주가와 주요 이동평균/EMA를 결합한 뷰
CREATE OR REPLACE VIEW v_stock_price_weekly_with_ma AS
SELECT
  p.symbol,
  p.week_start,
  p.week_end,
  p.open,
  p.high,
  p.low,
  p.adj_close AS close,
  p.volume,

  MAX(CASE WHEN i.indicator = 'sma_20_close'  THEN i.value END) AS sma_20,
  MAX(CASE WHEN i.indicator = 'sma_50_close'  THEN i.value END) AS sma_50,
  MAX(CASE WHEN i.indicator = 'sma_100_close' THEN i.value END) AS sma_100,
  MAX(CASE WHEN i.indicator = 'sma_200_close' THEN i.value END) AS sma_200,
  MAX(CASE WHEN i.indicator = 'ema_21_close'  THEN i.value END) AS ema_21

FROM stock_prices_weekly p
LEFT JOIN stock_indicators_weekly i
  ON p.symbol     = i.symbol
 AND p.week_start = i.week_start

GROUP BY
  p.symbol, p.week_start, p.week_end, p.open, p.high, p.low, p.close, p.volume;

-- US 일봉 주가와 주요 이동평균/EMA를 결합한 뷰
CREATE OR REPLACE VIEW v_us_stock_price_with_ma AS
SELECT
  p.symbol,
  p.date,
  p.open,
  p.high,
  p.low,
  p.adj_close AS close,
  p.volume,

  MAX(CASE WHEN i.indicator = 'sma_50_close'  THEN i.value END) AS sma_50,
  MAX(CASE WHEN i.indicator = 'sma_100_close' THEN i.value END) AS sma_100,
  MAX(CASE WHEN i.indicator = 'sma_150_close' THEN i.value END) AS sma_150,
  MAX(CASE WHEN i.indicator = 'sma_200_close' THEN i.value END) AS sma_200,
  MAX(CASE WHEN i.indicator = 'rs_line'       THEN i.value END) AS rs_line

FROM us_stock_prices p
LEFT JOIN us_stock_indicators i
  ON p.symbol = i.symbol
 AND p.date   = i.date

GROUP BY
  p.symbol, p.date, p.open, p.high, p.low, p.close, p.volume;

-- US 주봉 주가와 주요 이동평균/EMA를 결합한 뷰
CREATE OR REPLACE VIEW v_us_stock_price_weekly_with_ma AS
SELECT
  p.symbol,
  p.week_start,
  p.week_end,
  p.open,
  p.high,
  p.low,
  p.adj_close AS close,
  p.volume,

  MAX(CASE WHEN i.indicator = 'sma_20_close'  THEN i.value END) AS sma_20,
  MAX(CASE WHEN i.indicator = 'sma_50_close'  THEN i.value END) AS sma_50,
  MAX(CASE WHEN i.indicator = 'sma_100_close' THEN i.value END) AS sma_100,
  MAX(CASE WHEN i.indicator = 'sma_200_close' THEN i.value END) AS sma_200,
  MAX(CASE WHEN i.indicator = 'ema_21_close'  THEN i.value END) AS ema_21

FROM us_stock_prices_weekly p
LEFT JOIN us_stock_indicators_weekly i
  ON p.symbol     = i.symbol
 AND p.week_start = i.week_start

GROUP BY
  p.symbol, p.week_start, p.week_end, p.open, p.high, p.low, p.close, p.volume;

-- 코인 주봉 주가와 주요 이동평균/EMA를 결합한 뷰
CREATE OR REPLACE VIEW v_crypto_price_weekly_with_ma AS
SELECT
  p.symbol,
  p.week_start,
  p.week_end,
  p.open,
  p.high,
  p.low,
  p.close,
  p.volume_quote,

  MAX(CASE WHEN i.indicator = 'sma_20_close'  THEN i.value END) AS sma_20,
  MAX(CASE WHEN i.indicator = 'sma_50_close'  THEN i.value END) AS sma_50,
  MAX(CASE WHEN i.indicator = 'sma_100_close' THEN i.value END) AS sma_100,
  MAX(CASE WHEN i.indicator = 'sma_200_close' THEN i.value END) AS sma_200,
  MAX(CASE WHEN i.indicator = 'ema_21_close'  THEN i.value END) AS ema_21

FROM crypto_prices_weekly p
LEFT JOIN crypto_indicators_weekly i
  ON p.symbol     = i.symbol
 AND p.week_start = i.week_start

GROUP BY
  p.symbol, p.week_start, p.week_end, p.open, p.high, p.low, p.close, p.volume_quote;

-- KR 지수 가격과 주요 이동평균선을 결합한 뷰
CREATE OR REPLACE VIEW v_kr_index_price_with_ma AS
SELECT
  p.symbol,
  p.date,
  p.open,
  p.high,
  p.low,
  p.close,
  p.volume,

  MAX(CASE WHEN i.indicator = 'sma_50_close'  THEN i.value END) AS sma_50,
  MAX(CASE WHEN i.indicator = 'sma_100_close' THEN i.value END) AS sma_100,
  MAX(CASE WHEN i.indicator = 'sma_150_close' THEN i.value END) AS sma_150,
  MAX(CASE WHEN i.indicator = 'sma_200_close' THEN i.value END) AS sma_200

FROM kr_index_prices p
LEFT JOIN kr_index_indicators i
  ON p.symbol = i.symbol
 AND p.date   = i.date

GROUP BY
  p.symbol, p.date, p.open, p.high, p.low, p.close, p.volume;

-- KR 지수 주봉 가격과 주요 이동평균선을 결합한 뷰
CREATE OR REPLACE VIEW v_kr_index_price_weekly_with_ma AS
SELECT
  p.symbol, p.week_start, p.week_end,
  p.open, p.high, p.low, p.close, p.volume,
  MAX(CASE WHEN i.indicator = 'sma_5_close'  THEN i.value END) AS sma_5,
  MAX(CASE WHEN i.indicator = 'sma_20_close' THEN i.value END) AS sma_20,
  MAX(CASE WHEN i.indicator = 'ema_12_close' THEN i.value END) AS ema_12,
  MAX(CASE WHEN i.indicator = 'ema_26_close' THEN i.value END) AS ema_26
FROM kr_index_prices_weekly p
LEFT JOIN kr_index_indicators_weekly i
  ON p.symbol = i.symbol AND p.week_start = i.week_start
GROUP BY p.symbol, p.week_start, p.week_end, p.open, p.high, p.low, p.close, p.volume;

-- US 지수 가격과 주요 이동평균선을 결합한 뷰
CREATE OR REPLACE VIEW v_us_index_price_with_ma AS
SELECT
  p.symbol,
  p.date,
  p.open,
  p.high,
  p.low,
  p.close,
  p.volume,

  MAX(CASE WHEN i.indicator = 'sma_50_close'  THEN i.value END) AS sma_50,
  MAX(CASE WHEN i.indicator = 'sma_100_close' THEN i.value END) AS sma_100,
  MAX(CASE WHEN i.indicator = 'sma_150_close' THEN i.value END) AS sma_150,
  MAX(CASE WHEN i.indicator = 'sma_200_close' THEN i.value END) AS sma_200

FROM us_index_prices p
LEFT JOIN us_index_indicators i
  ON p.symbol = i.symbol
 AND p.date   = i.date

GROUP BY
  p.symbol, p.date, p.open, p.high, p.low, p.close, p.volume;

-- US 지수 주봉 가격과 주요 이동평균선을 결합한 뷰
CREATE OR REPLACE VIEW v_us_index_price_weekly_with_ma AS
SELECT
  p.symbol,
  p.week_start,
  p.week_end,
  p.open,
  p.high,
  p.low,
  p.close,
  p.volume,

  MAX(CASE WHEN i.indicator = 'sma_5_close'  THEN i.value END) AS sma_5,
  MAX(CASE WHEN i.indicator = 'sma_20_close' THEN i.value END) AS sma_20,
  MAX(CASE WHEN i.indicator = 'sma_40_close' THEN i.value END) AS sma_40

FROM us_index_prices_weekly p
LEFT JOIN us_index_indicators_weekly i
  ON p.symbol     = i.symbol
 AND p.week_start = i.week_start

GROUP BY
  p.symbol, p.week_start, p.week_end, p.open, p.high, p.low, p.close, p.volume;


CREATE OR REPLACE VIEW v_watchlist_items_kr AS
SELECT
  w.*,
  sm.name,
  sm.market AS kr_market,
  sm.sector,
  sm.industry
FROM watchlist_items w
LEFT JOIN symbol_master sm
  ON sm.symbol = w.symbol
WHERE w.market = 'KR';


-- ============================================
-- Minervini Trend Template Screening Tables
-- ============================================

-- Korean Stock Minervini Screening Results
CREATE TABLE IF NOT EXISTS minervini_screen_results_kr (
  symbol             VARCHAR(32)  NOT NULL COMMENT 'Stock symbol',
  date               DATE         NOT NULL COMMENT 'Screening date',
  market             VARCHAR(16)  NOT NULL COMMENT 'Market: KOSPI/KOSDAQ/ETF',
  rs_rating          DECIMAL(5,1) NULL COMMENT 'IBD RS Rating (1-99)',
  is_blue_dot        TINYINT      NULL COMMENT 'Blue Dot signal (0/1)',
  screen_config_hash CHAR(40)     NOT NULL COMMENT 'Hash of screening config',
  failed_reason      VARCHAR(512) NULL COMMENT 'Reason for failure (unused - only passing symbols stored)',
  created_at         TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation timestamp',
  PRIMARY KEY (symbol, date, screen_config_hash),
  KEY idx_date_market_config (date, market, screen_config_hash),
  KEY idx_date_market_symbol (date, market, symbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Minervini Trend Template screening results for Korean stocks';

-- US Stock Minervini Screening Results
CREATE TABLE IF NOT EXISTS minervini_screen_results_us (
  symbol             VARCHAR(32)  NOT NULL COMMENT 'Stock symbol',
  date               DATE         NOT NULL COMMENT 'Screening date',
  market             VARCHAR(16)  NOT NULL COMMENT 'Market: NYSE/NASDAQ/ETF',
  rs_rating          DECIMAL(5,1) NULL COMMENT 'IBD RS Rating (1-99)',
  is_blue_dot        TINYINT      NULL COMMENT 'Blue Dot signal (0/1)',
  screen_config_hash CHAR(40)     NOT NULL COMMENT 'Hash of screening config',
  failed_reason      VARCHAR(512) NULL COMMENT 'Reason for failure (unused - only passing symbols stored)',
  created_at         TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation timestamp',
  PRIMARY KEY (symbol, date, screen_config_hash),
  KEY idx_date_market_config (date, market, screen_config_hash)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Minervini Trend Template screening results for US stocks';

-- KR sector snapshot for screening/pivot query optimization
CREATE TABLE IF NOT EXISTS kr_sector_snapshot (
  date               DATE         NOT NULL,
  market             VARCHAR(16)  NOT NULL,
  sector             VARCHAR(128) NULL,
  symbol             VARCHAR(32)  NOT NULL,
  name               VARCHAR(128) NULL,
  close              DECIMAL(18,4)  NULL,
  sma_50             DECIMAL(28,10) NULL,
  sma_150            DECIMAL(28,10) NULL,
  sma_200            DECIMAL(28,10) NULL,
  rs_rating          DECIMAL(5,1)   NULL,
  is_blue_dot        TINYINT        NULL,
  is_pass            TINYINT      NOT NULL DEFAULT 0,
  PRIMARY KEY (date, market, symbol),
  KEY idx_date_market_sector (date, market, sector),
  KEY idx_date_market_sector_pass (date, market, sector, is_pass)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
