-- US Stock Weekly Tables Migration
-- Run this script to add US weekly tables to an existing database
-- Usage: mysql -h HOST -u USER -p DATABASE < add_us_weekly_tables.sql

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

-- US Weekly price with moving averages view
CREATE OR REPLACE VIEW v_us_stock_price_weekly_with_ma AS
SELECT
  p.symbol,
  p.week_start,
  p.week_end,
  p.open,
  p.high,
  p.low,
  p.close,
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
