-- US Index Weekly Tables Migration
-- Run this script to add US Index weekly tables to an existing database
-- Usage: mysql -h HOST -u USER -p DATABASE < add_us_index_weekly_tables.sql

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

-- US Index Weekly price with moving averages view
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
