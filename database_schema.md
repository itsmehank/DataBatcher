# DataBatcher Database Schema
**Last Updated**: 2026-01-19
**Database**: MySQL 8.0
**Charset**: utf8mb4

---

## Table of Contents
1. [Overview](#overview)
2. [Active Tables](#active-tables)
   - [stock_prices](#1-stock_prices)
   - [stock_indicators](#2-stock_indicators)
   - [symbol_master](#3-symbol_master)
3. [Reserved Tables](#reserved-tables)
   - [sync_log](#4-sync_log)
   - [crypto_prices](#5-crypto_prices)
4. [Data Flow](#data-flow)
5. [Index Strategy](#index-strategy)

---

## Overview

### Current Database Statistics

| Table | Status | Row Count | Purpose |
|-------|--------|-----------|---------|
| **stock_prices** | ✅ Active | 22,210 | OHLCV price data storage |
| **stock_indicators** | ✅ Active | 44,048 | Technical indicators (SMA, EMA, etc.) |
| **symbol_master** | ✅ Active | 2,894 | KRX symbol catalog and status |
| sync_log | 📋 Reserved | 0 | ETL job execution tracking |
| crypto_prices | 📋 Reserved | 0 | Cryptocurrency price data |

### Database Configuration
```yaml
Engine: InnoDB
Charset: utf8mb4
Collation: utf8mb4_general_ci
Timezone: System default (KST/UTC+9)
```

---

## Active Tables

### 1. stock_prices

**Purpose**: Stores daily OHLCV (Open, High, Low, Close, Volume) price data for Korean stocks

**Schema**:
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
  currency      VARCHAR(8) NULL,
  market        VARCHAR(16) NOT NULL,
  source        VARCHAR(16) NOT NULL,
  etl_loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (symbol, date),
  KEY idx_date (date),
  KEY idx_market_date (market, date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**Column Details**:

| Column | Type | Null | Description | Example |
|--------|------|------|-------------|---------|
| symbol | VARCHAR(32) | NO | Stock symbol code | `005930` (삼성전자) |
| date | DATE | NO | Trading date | `2024-01-02` |
| open | DECIMAL(18,4) | YES | Opening price | `10270.0000` |
| high | DECIMAL(18,4) | YES | Highest price | `10580.0000` |
| low | DECIMAL(18,4) | YES | Lowest price | `10270.0000` |
| close | DECIMAL(18,4) | YES | Closing price | `10490.0000` |
| adj_close | DECIMAL(18,4) | YES | Adjusted closing price | NULL (not used) |
| volume | BIGINT | YES | Trading volume | `238593` |
| currency | VARCHAR(8) | YES | Currency code | NULL (KRW assumed) |
| market | VARCHAR(16) | NO | Market identifier | `XKRX` |
| source | VARCHAR(16) | NO | Data source | `FDR` |
| etl_loaded_at | TIMESTAMP | NO | ETL timestamp | `2026-01-19 23:38:47` |

**Primary Key**: `(symbol, date)` - Composite key ensures one row per symbol per date

**Indexes**:
- `idx_date`: Fast date-range queries (e.g., "all stocks on 2024-01-02")
- `idx_market_date`: Market-specific queries (e.g., "KOSPI on date range")

**Sample Data**:
```json
{
  "symbol": "000020",
  "date": "2024-01-02",
  "open": 10270.0000,
  "high": 10580.0000,
  "low": 10270.0000,
  "close": 10490.0000,
  "adj_close": null,
  "volume": 238593,
  "currency": null,
  "market": "XKRX",
  "source": "FDR",
  "etl_loaded_at": "2026-01-19 23:38:47"
}
```

**Data Source**: FinanceDataReader (FDR) → Yahoo Finance API

**Update Frequency**: Daily (via `scripts/daily_update.py`)

**Storage Estimate**: ~240 rows/symbol/year → 2,894 symbols × 240 = ~700K rows/year

---

### 2. stock_indicators

**Purpose**: Stores calculated technical indicators in long-form (EAV pattern)

**Schema**:
```sql
CREATE TABLE stock_indicators (
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
```

**Column Details**:

| Column | Type | Null | Description | Example |
|--------|------|------|-------------|---------|
| symbol | VARCHAR(32) | NO | Stock symbol code | `000020` |
| date | DATE | NO | Calculation date | `2024-01-02` |
| indicator | VARCHAR(64) | NO | Indicator name + params | `ema_12_close` |
| params_hash | CHAR(40) | NO | SHA1 hash of parameters | `e1263f1c0f1d8ef1...` |
| value | DECIMAL(28,10) | YES | Indicator value | `10490.0000000000` |
| market | VARCHAR(16) | NO | Market identifier | `KOSPI` |
| source | VARCHAR(16) | NO | Source data origin | `FDR` |
| etl_loaded_at | TIMESTAMP | NO | ETL timestamp | `2026-01-19 23:38:47` |

**Primary Key**: `(symbol, date, indicator, params_hash)` - Supports multiple parameter sets per indicator

**Indexes**:
- `idx_indicator_date`: Fast indicator-specific queries (e.g., "all EMA values on date")
- `idx_symbol_date`: Symbol timeline queries (e.g., "all indicators for symbol")

**Sample Data**:
```json
{
  "symbol": "000020",
  "date": "2024-01-03",
  "indicator": "ema_12_close",
  "params_hash": "e1263f1c0f1d8ef1f79b7ed165a28d88dce79783",
  "value": 10499.2307692308,
  "market": "KOSPI",
  "source": "FDR",
  "etl_loaded_at": "2026-01-19 23:38:47"
}
```

**Currently Configured Indicators**:
```yaml
# From config/settings.yaml
indicators:
  pipeline:
    - name: sma
      params: { window: 5, column: close }
    - name: sma
      params: { window: 20, column: close }
    - name: ema
      params: { window: 12, column: close }
    - name: ema
      params: { window: 26, column: close }
```

**Indicator Naming Convention**:
- Format: `{indicator}_{window}_{column}`
- Examples:
  - `sma_5_close`: 5-day Simple Moving Average of close price
  - `ema_12_close`: 12-day Exponential Moving Average of close price
  - `rsi_14_close`: 14-day Relative Strength Index (future)

**Storage Estimate**: 4 indicators × 240 days × 2,894 symbols = ~2.8M rows/year

---

### 3. symbol_master

**Purpose**: Master catalog of all KRX (Korean Exchange) listed symbols with status tracking

**Schema**:
```sql
CREATE TABLE symbol_master (
  symbol        VARCHAR(32) PRIMARY KEY,
  market        VARCHAR(16) NOT NULL,
  name          VARCHAR(128) NULL,
  status        VARCHAR(16) NOT NULL,
  first_date    DATE NULL,
  last_date     DATE NULL,
  updated_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**Column Details**:

| Column | Type | Null | Description | Example |
|--------|------|------|-------------|---------|
| symbol | VARCHAR(32) | NO | Stock symbol code (PK) | `005930` |
| market | VARCHAR(16) | NO | Exchange market | `KOSPI`, `KOSDAQ`, `KONEX` |
| name | VARCHAR(128) | YES | Company name (Korean) | `삼성전자` |
| status | VARCHAR(16) | NO | Listing status | `ACTIVE`, `DELISTED` |
| first_date | DATE | YES | First available data date | NULL (computed) |
| last_date | DATE | YES | Last available data date | NULL (computed) |
| updated_at | TIMESTAMP | NO | Last sync timestamp | `2026-01-19 23:38:35` |

**Status Values**:
- `ACTIVE`: Currently trading
- `DELISTED`: Removed from exchange
- `IPO_PENDING`: Future use (pre-listing)

**Sample Data**:
```json
{
  "symbol": "005930",
  "market": "KOSPI",
  "name": "삼성전자",
  "status": "ACTIVE",
  "first_date": null,
  "last_date": null,
  "updated_at": "2026-01-19 23:38:35"
}
```

**Data Source**: `FinanceDataReader.StockListing('KRX')`

**Update Frequency**: Weekly (via `scripts/sync_symbol_master.py`)

**Market Distribution** (as of 2026-01-19):
| Market | Count | Percentage |
|--------|-------|------------|
| KOSPI | ~950 | 33% |
| KOSDAQ | ~1,700 | 59% |
| KONEX | ~100 | 3% |
| Others | ~144 | 5% |
| **Total** | **2,894** | **100%** |

---

## Reserved Tables

### 4. sync_log

**Purpose**: ETL job execution tracking and audit trail (not yet implemented)

**Schema**:
```sql
CREATE TABLE sync_log (
  id            BIGINT AUTO_INCREMENT PRIMARY KEY,
  job_name      VARCHAR(64) NOT NULL,
  market        VARCHAR(16) NOT NULL,
  symbol        VARCHAR(32) NULL,
  start_time    DATETIME NOT NULL,
  end_time      DATETIME NULL,
  rows_processed INT DEFAULT 0,
  status        VARCHAR(16) NOT NULL,
  message       VARCHAR(1024) NULL,
  created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_job_market_time (job_name, market, start_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**Status**: 🔜 Not yet used (planned for future monitoring feature)

**Planned Usage**:
```python
# Future implementation example
log_entry = {
    "job_name": "daily_update",
    "market": "KOSPI",
    "symbol": None,  # NULL for batch jobs
    "start_time": "2024-01-02 17:00:00",
    "end_time": "2024-01-02 17:15:00",
    "rows_processed": 22500,
    "status": "SUCCESS",
    "message": "Collected 950 symbols, 22,500 rows"
}
```

---

### 5. crypto_prices

**Purpose**: Cryptocurrency price data storage (reserved for future use)

**Schema**:
```sql
CREATE TABLE crypto_prices (
  symbol        VARCHAR(32)  NOT NULL,
  date          DATE         NOT NULL,
  open          DECIMAL(28,10),
  high          DECIMAL(28,10),
  low           DECIMAL(28,10),
  close         DECIMAL(28,10),
  volume        DECIMAL(28,10),
  market        VARCHAR(16) NOT NULL,
  source        VARCHAR(16) NOT NULL,
  etl_loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (symbol, date),
  KEY idx_date (date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**Status**: 🔜 Not yet used (future cryptocurrency support)

**Differences from stock_prices**:
- Higher precision: `DECIMAL(28,10)` (crypto trades at fractional values)
- No `currency` field (assumed to be vs. USD or KRW)
- No `adj_close` (cryptocurrencies don't have stock splits)

---

## Data Flow

### Collection Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                     Data Collection Flow                         │
└─────────────────────────────────────────────────────────────────┘

1. Symbol Sync (Weekly)
   ┌──────────────────────┐
   │ FinanceDataReader    │ StockListing('KRX')
   │ (Yahoo Finance)      │────────────────────┐
   └──────────────────────┘                    │
                                               ▼
                                    ┌──────────────────┐
                                    │  symbol_master   │
                                    │  (2,894 symbols) │
                                    └──────────────────┘

2. Price Collection (Daily)
   ┌──────────────────────┐
   │ FinanceDataReader    │ DataReader(symbol, start, end)
   │ (Yahoo Finance)      │────────────────────┐
   └──────────────────────┘                    │
                                               ▼
                                    ┌──────────────────┐
                                    │  stock_prices    │
                                    │  (22,210 rows)   │
                                    └──────────────────┘
                                               │
                                               │ Load historical data
                                               ▼
3. Indicator Calculation                ┌──────────────┐
   ┌──────────────────────┐             │ Price Data   │
   │ IndicatorPipeline    │◄────────────│ (250 days)   │
   │ - SMA (5, 20)        │             └──────────────┘
   │ - EMA (12, 26)       │
   └──────────────────────┘
              │
              │ Calculate indicators
              ▼
   ┌──────────────────────┐
   │ stock_indicators     │
   │ (44,048 rows)        │
   │ - sma_5_close        │
   │ - sma_20_close       │
   │ - ema_12_close       │
   │ - ema_26_close       │
   └──────────────────────┘
```

### Scripts and Tables Mapping

| Script | Reads From | Writes To | Frequency |
|--------|-----------|-----------|-----------|
| `sync_symbol_master.py` | FDR API | `symbol_master` | Weekly |
| `bulk_update.py` | FDR API, `symbol_master` | `stock_prices`, `stock_indicators` | Initial/Backfill |
| `daily_update.py` | FDR API, `symbol_master`, `stock_prices` | `stock_prices`, `stock_indicators` | Daily |

### Update Modes

**INSERT ONLY Mode** (used by `bulk_update.py`):
```sql
INSERT IGNORE INTO stock_prices (...) VALUES (...)
-- Preserves existing data, only inserts new rows
```

**UPSERT Mode** (default, used by `daily_update.py`):
```sql
INSERT INTO stock_prices (...) VALUES (...)
ON DUPLICATE KEY UPDATE
  open = VALUES(open),
  high = VALUES(high),
  ...
-- Overwrites existing data with new values
```

---

## Index Strategy

### Performance Optimization

**stock_prices**:
```sql
PRIMARY KEY (symbol, date)        -- Fast point lookups
KEY idx_date (date)                -- Market-wide queries by date
KEY idx_market_date (market, date) -- Market-specific time series
```

**stock_indicators**:
```sql
PRIMARY KEY (symbol, date, indicator, params_hash)  -- Unique constraint
KEY idx_indicator_date (indicator, date)            -- Indicator analysis
KEY idx_symbol_date (symbol, date)                  -- Symbol timeline
```

### Query Patterns

**Get all prices for a symbol**:
```sql
SELECT * FROM stock_prices
WHERE symbol = '005930'
ORDER BY date DESC
LIMIT 100;
-- Uses PRIMARY KEY
```

**Get all stocks on a specific date**:
```sql
SELECT * FROM stock_prices
WHERE date = '2024-01-02';
-- Uses idx_date
```

**Get indicator time series**:
```sql
SELECT date, value FROM stock_indicators
WHERE symbol = '005930'
  AND indicator = 'ema_12_close'
  AND params_hash = 'e1263f1c0f...'
ORDER BY date;
-- Uses PRIMARY KEY range scan
```

**Cross-indicator analysis**:
```sql
SELECT s.date, s.value as sma_5, e.value as ema_12
FROM stock_indicators s
JOIN stock_indicators e
  ON s.symbol = e.symbol AND s.date = e.date
WHERE s.symbol = '005930'
  AND s.indicator = 'sma_5_close'
  AND e.indicator = 'ema_12_close'
  AND s.date >= '2024-01-01';
-- Uses idx_symbol_date
```

---

## Data Types and Precision

### Price Precision
```sql
DECIMAL(18,4)  -- Supports prices up to 99,999,999,999,999.9999
               -- Example: 123,456.7890 (adequate for KRX stocks)
```

### Indicator Precision
```sql
DECIMAL(28,10) -- High precision for calculated values
               -- Example: 10499.2307692308 (EMA requires precision)
```

### Volume Storage
```sql
BIGINT         -- Supports up to 9,223,372,036,854,775,807
               -- Example: 17,142,847 (adequate for daily volume)
```

---

## Maintenance

### Regular Tasks

**Daily**:
```bash
# Update all active symbols
python scripts/daily_update.py --all --force
```

**Weekly**:
```bash
# Sync symbol master (catch new listings/delistings)
python scripts/sync_symbol_master.py
```

**Monthly** (recommended):
```sql
-- Check table sizes
SELECT
  table_name,
  ROUND(((data_length + index_length) / 1024 / 1024), 2) AS size_mb
FROM information_schema.TABLES
WHERE table_schema = 'market'
ORDER BY size_mb DESC;

-- Check data freshness
SELECT
  MAX(date) as latest_date,
  COUNT(DISTINCT symbol) as symbol_count,
  COUNT(*) as total_rows
FROM stock_prices;
```

### Backup Strategy

**Recommended**:
```bash
# Daily backup
mysqldump -h 127.0.0.1 -u YOUR_DB_USER -p market \
  --single-transaction \
  --routines --triggers \
  > backup_$(date +%Y%m%d).sql

# Compress
gzip backup_$(date +%Y%m%d).sql
```

---

## Storage Estimates

### Current Usage (2026-01-19)
| Table | Rows | Est. Size |
|-------|------|-----------|
| stock_prices | 22,210 | ~2 MB |
| stock_indicators | 44,048 | ~3 MB |
| symbol_master | 2,894 | ~0.5 MB |
| **Total** | **69,152** | **~6 MB** |

### Projected Growth (1 Year)
| Table | Rows/Year | Est. Size/Year |
|-------|-----------|----------------|
| stock_prices | ~700,000 | ~70 MB |
| stock_indicators | ~2,800,000 | ~200 MB |
| symbol_master | 3,000 | ~0.5 MB |
| **Total** | **~3.5M** | **~270 MB** |

### Projected Growth (5 Years)
| Table | Rows | Est. Size |
|-------|------|-----------|
| stock_prices | ~3.5M | ~350 MB |
| stock_indicators | ~14M | ~1 GB |
| symbol_master | 3,500 | ~0.5 MB |
| **Total** | **~17.5M** | **~1.4 GB** |

---

## Character Encoding

**All tables use UTF-8 (utf8mb4)**:
```sql
DEFAULT CHARSET=utf8mb4
```

This supports:
- Korean characters: `삼성전자`, `SK하이닉스`
- Emojis (if needed in future)
- Full Unicode range

**Connection String**:
```
mysql://YOUR_DB_USER:YOUR_DB_PASSWORD@127.0.0.1:3306/market?charset=utf8mb4
```

---

## Future Enhancements

### Planned Tables
- [ ] `portfolio` - User portfolio tracking
- [ ] `backtest_results` - Strategy backtest metrics
- [ ] `alerts` - Price/indicator alert rules

### Schema Improvements
- [ ] Add `market_cap` to `symbol_master` (for filtering)
- [ ] Add `sector` and `industry` to `symbol_master`
- [ ] Implement `sync_log` for job monitoring
- [ ] Add partitioning for `stock_prices` (by year)
- [ ] Add materialized views for common aggregations

---

## References

- **Schema Definition**: `docker/mysql/init/01_schema.sql`
- **DB Manager**: `core/db_manager.py`
- **Configuration**: `config/settings.yaml`
- **Data Sources**: FinanceDataReader (Yahoo Finance backend)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-19 | Initial schema documentation |
