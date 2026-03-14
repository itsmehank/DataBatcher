-- Migration: Add Minervini Trend Template Screening Tables
-- Date: 2026-02-09
-- Description: Creates tables to store pre-computed Minervini screening results

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
  KEY idx_date_market_config (date, market, screen_config_hash)
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
