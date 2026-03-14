-- Migration: Add KR Index Weekly tables (KOSPI/KOSDAQ index weekly data)
-- Run: mysql -h 127.0.0.1 -u marketu -pmarketp market < scripts/migrations/add_kr_index_weekly_tables.sql

-- kr_index_prices_weekly: 지수 주봉 가격 (adj_close 없음 - 지수는 수정주가 불필요)
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

-- kr_index_indicators_weekly: 지수 주봉 지표 (long form)
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

-- View: 지수 주봉 가격 + 이동평균선
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
