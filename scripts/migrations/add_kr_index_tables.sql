-- Migration: Add KR Index tables (KOSPI/KOSDAQ index data)
-- Run: mysql -h 127.0.0.1 -u marketu -pmarketp market < scripts/migrations/add_kr_index_tables.sql

-- kr_index_master: 지수 마스터 (KOSPI 1001, KOSDAQ 2001)
CREATE TABLE IF NOT EXISTS kr_index_master (
  symbol        VARCHAR(32) PRIMARY KEY,        -- '1001', '2001'
  market        VARCHAR(16) NOT NULL,           -- KOSPI / KOSDAQ
  name          VARCHAR(128) NULL,              -- '코스피', '코스닥'
  status        VARCHAR(16) NOT NULL DEFAULT 'ACTIVE',
  etl_loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- kr_index_prices: 지수 일봉 (adj_close 없음 - 지수는 수정주가 불필요)
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

-- kr_index_indicators: 지수 지표 (long form)
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

-- View: 지수 가격 + 이동평균선
CREATE OR REPLACE VIEW v_kr_index_price_with_ma AS
SELECT
  p.symbol,
  p.date,
  p.open,
  p.high,
  p.low,
  p.close,
  p.volume,

  MAX(CASE WHEN i.indicator = 'sma'  AND i.params_hash = SHA1('{"column":"close","window":5}')  THEN i.value END) AS sma_5,
  MAX(CASE WHEN i.indicator = 'sma'  AND i.params_hash = SHA1('{"column":"close","window":20}') THEN i.value END) AS sma_20,
  MAX(CASE WHEN i.indicator = 'ema'  AND i.params_hash = SHA1('{"column":"close","window":12}') THEN i.value END) AS ema_12,
  MAX(CASE WHEN i.indicator = 'ema'  AND i.params_hash = SHA1('{"column":"close","window":26}') THEN i.value END) AS ema_26

FROM kr_index_prices p
LEFT JOIN kr_index_indicators i
  ON p.symbol = i.symbol
 AND p.date   = i.date

GROUP BY
  p.symbol, p.date, p.open, p.high, p.low, p.close, p.volume;
