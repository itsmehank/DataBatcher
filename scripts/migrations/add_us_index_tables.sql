-- Migration: Add US Index tables (S&P 500, Dow Jones, NASDAQ Composite)
-- Run: mysql -h 127.0.0.1 -u marketu -pmarketp market < scripts/migrations/add_us_index_tables.sql

-- us_index_master: 미국 지수 마스터 (US500, DJI, IXIC)
CREATE TABLE IF NOT EXISTS us_index_master (
  symbol        VARCHAR(32) PRIMARY KEY,        -- 'US500', 'DJI', 'IXIC'
  market        VARCHAR(16) NOT NULL,           -- SP500 / DJI / IXIC
  name          VARCHAR(128) NULL,              -- 'S&P 500', 'Dow Jones Industrial Average', ...
  status        VARCHAR(16) NOT NULL DEFAULT 'ACTIVE',
  etl_loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- us_index_prices: 미국 지수 일봉 (adj_close 없음 - 지수는 수정주가 불필요)
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

-- us_index_indicators: 미국 지수 지표 (long form)
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

-- View: 미국 지수 가격 + 이동평균선 (SMA 5/20/40)
CREATE OR REPLACE VIEW v_us_index_price_with_ma AS
SELECT
  p.symbol,
  p.date,
  p.open,
  p.high,
  p.low,
  p.close,
  p.volume,

  MAX(CASE WHEN i.indicator = 'sma_5_close'  THEN i.value END) AS sma_5,
  MAX(CASE WHEN i.indicator = 'sma_20_close' THEN i.value END) AS sma_20,
  MAX(CASE WHEN i.indicator = 'sma_40_close' THEN i.value END) AS sma_40

FROM us_index_prices p
LEFT JOIN us_index_indicators i
  ON p.symbol = i.symbol
 AND p.date   = i.date

GROUP BY
  p.symbol, p.date, p.open, p.high, p.low, p.close, p.volume;
