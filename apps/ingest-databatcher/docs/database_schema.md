# DataBatcher Database Schema
**Last Updated**: 2026-05-07
**Database**: MySQL 8.0
**Charset**: utf8mb4
**Schema Source**: `db/init/01_schema.sql` + running DB (`information_schema`/`SHOW CREATE`) + `db/migrations/` (Alembic + raw SQL)

---

## Table of Contents
1. [Overview](#overview)
2. [KR Stock Tables](#kr-stock-tables)
3. [KR Stock Weekly Tables](#kr-stock-weekly-tables)
4. [KR Index Tables](#kr-index-tables)
5. [KR Index Weekly Tables](#kr-index-weekly-tables)
6. [US Stock Tables](#us-stock-tables)
7. [US Stock Weekly Tables](#us-stock-weekly-tables)
8. [US Index Tables](#us-index-tables)
9. [US Index Weekly Tables](#us-index-weekly-tables)
10. [Crypto Tables](#crypto-tables)
11. [Crypto Weekly Tables](#crypto-weekly-tables)
12. [Minervini Screen Tables](#minervini-screen-tables)
13. [LLM Analysis Tables](#llm-analysis-tables)
14. [Auth & User Tables](#auth--user-tables)
15. [System Tables](#system-tables)
16. [Database Views](#database-views)
17. [Scripts and Tables Mapping](#scripts-and-tables-mapping)
18. [Index Strategy](#index-strategy)
19. [Data Types and Precision](#data-types-and-precision)

---

## Overview

### Table Summary

| # | Table | Market | Timeframe | adj_close | Indicator Config Key |
|---|-------|--------|-----------|-----------|---------------------|
| 1 | `symbol_master` | KR (KOSPI/KOSDAQ/KONEX) | - | - | - |
| 2 | `stock_prices` | KR | Daily | O | `indicators` |
| 3 | `stock_indicators` | KR | Daily | - | `indicators` |
| 4 | `kr_sector_snapshot`* | KR | Daily | - | - |
| 5 | `stock_prices_weekly` | KR | Weekly | O | `indicators_weekly` |
| 6 | `stock_indicators_weekly` | KR | Weekly | - | `indicators_weekly` |
| 7 | `kr_index_master` | KR (KOSPI/KOSDAQ Index) | - | - | - |
| 8 | `kr_index_prices` | KR Index | Daily | X | `indicators_kr_index` |
| 9 | `kr_index_indicators` | KR Index | Daily | - | `indicators_kr_index` |
| 10 | `kr_index_prices_weekly` | KR Index | Weekly | X | `indicators_kr_index_weekly` |
| 11 | `kr_index_indicators_weekly` | KR Index | Weekly | - | `indicators_kr_index_weekly` |
| 12 | `us_symbol_master` | US (NYSE/NASDAQ/ETF) | - | - | - |
| 13 | `us_stock_prices` | US | Daily | O | `indicators_us` |
| 14 | `us_stock_indicators` | US | Daily | - | `indicators_us` |
| 15 | `us_stock_prices_weekly` | US | Weekly | O | `indicators_us_weekly` |
| 16 | `us_stock_indicators_weekly` | US | Weekly | - | `indicators_us_weekly` |
| 17 | `us_index_master` | US (SP500/DJI/IXIC) | - | - | - |
| 18 | `us_index_prices` | US Index | Daily | X | `indicators_us_index` |
| 19 | `us_index_indicators` | US Index | Daily | - | `indicators_us_index` |
| 20 | `us_index_prices_weekly` | US Index | Weekly | X | `indicators_us_index_weekly` |
| 21 | `us_index_indicators_weekly` | US Index | Weekly | - | `indicators_us_index_weekly` |
| 22 | `crypto_symbol_master` | Crypto (Binance USDT) | - | - | - |
| 23 | `crypto_prices_daily` | Crypto | Daily | - | `indicators_crypto_daily` |
| 24 | `crypto_indicators_daily` | Crypto | Daily | - | `indicators_crypto_daily` |
| 25 | `crypto_prices_weekly` | Crypto | Weekly | - | `indicators_crypto_weekly` |
| 26 | `crypto_indicators_weekly` | Crypto | Weekly | - | `indicators_crypto_weekly` |
| 27 | `minervini_screen_results_kr` | KR | Daily | - | `minervini_kr` |
| 28 | `minervini_screen_results_us` | US | Daily | - | `minervini_us` |
| 29 | `daily_analysis_kr` | KR | Daily | - | LLM (Phase 1) |
| 30 | `daily_analysis_us` | US | Daily | - | LLM (Phase 1) |
| 31 | `llm_calls` | System | - | - | LLM call log (헌법 §2.5) |
| 32 | `users` | Auth | - | - | - |
| 33 | `minervini_list_selection` | UI | - | - | - |
| 34 | `sync_log` | System | - | - | ETL + LLM monitoring |
| 35 | `kr_sector_snapshot` | KR | Daily | - | - |
| 36 | `watchlist_items` | Legacy | - | - | (미사용 — Phase 6에서 제거 검토) |
| 37 | `alembic_version` | System | - | - | Alembic migration tracker |

> Running DB 기준 객체 수 (DEV, 2026-05-07): **BASE TABLE 36개 + VIEW 10개**.
> 과거 `metrics` 테이블은 제거됨. Phase 1에서 `daily_analysis_kr/us`, `llm_calls` 신설(ADR-009).
> P0.5에서 `minervini_screen_results_*`에 `conditions_met JSON` 컬럼 추가(ADR-009 결정 3).

### Database Configuration
```yaml
Engine: InnoDB
Charset: utf8mb4
Collation: utf8mb4_0900_ai_ci
Timezone: System default (KST/UTC+9)
```

---

## KR Stock Tables

### symbol_master

**Purpose**: KRX 상장 종목 마스터 (KOSPI/KOSDAQ/KONEX)

```sql
CREATE TABLE symbol_master (
  symbol        VARCHAR(32) PRIMARY KEY,
  market        VARCHAR(16) NOT NULL,      -- KOSPI / KOSDAQ / KONEX / ETF
  symbol_type   VARCHAR(16) NULL,          -- STOCK / ETF
  name          VARCHAR(128) NULL,
  status        VARCHAR(16) NOT NULL,      -- ACTIVE / DELISTED
  sector        VARCHAR(128) NULL,         -- pykrx 대분류 (26개)
  sector_detail VARCHAR(256) NULL,         -- FDR KRX-DESC 세분류 (162개)
  industry      VARCHAR(512) NULL,         -- FDR KRX-DESC Industry
  sector_source VARCHAR(32) NULL,          -- pykrx+fdr / pykrx / fdr
  sector_updated_at TIMESTAMP NULL,
  first_date    DATE NULL,
  last_date     DATE NULL,
  updated_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_market_status_sector_name (market, status, sector, name),
  KEY idx_market_status_sector_symbol (market, status, sector, symbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| symbol | VARCHAR(32) | 종목 코드 (PK) | `005930` |
| market | VARCHAR(16) | 시장 구분 | `KOSPI`, `KOSDAQ`, `KONEX`, `ETF` |
| symbol_type | VARCHAR(16) | 종목 유형 | `STOCK`, `ETF` |
| name | VARCHAR(128) | 종목명 | `삼성전자` |
| status | VARCHAR(16) | 상태 | `ACTIVE`, `DELISTED` |
| sector | VARCHAR(128) | pykrx 대분류 업종 | `전기전자`, `서비스업` |
| sector_detail | VARCHAR(256) | FDR 세분류 업종 | `반도체`, `소프트웨어` |
| industry | VARCHAR(512) | FDR 산업 분류 | `반도체와반도체장비` |
| sector_source | VARCHAR(32) | 섹터 데이터 출처 | `pykrx+fdr`, `pykrx`, `fdr` |
| sector_updated_at | TIMESTAMP | 섹터 정보 갱신 시각 | `2026-02-08 12:00:00` |
| first_date | DATE | 최초 데이터 일자 | NULL |
| last_date | DATE | 최종 데이터 일자 | NULL |

**Indexes**:
- `idx_market_status_sector_name`: `(market, status, sector, name)` — 시장/상태/섹터별 정렬 조회 최적화
- `idx_market_status_sector_symbol`: `(market, status, sector, symbol)` — 시장/상태/섹터 필터 + 심볼 조인 최적화

**Data Source**: pykrx + FDR | **Update Script**: `sync_symbol_master.py` (Weekly)

---

### stock_prices

**Purpose**: KR 주식 일봉 OHLCV

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
  market        VARCHAR(16) NOT NULL,      -- KOSPI / KOSDAQ / KONEX
  source        VARCHAR(16) NOT NULL,      -- pykrx
  etl_loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (symbol, date),
  KEY idx_date (date),
  KEY idx_market_date (market, date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**Data Source**: pykrx | **Update Script**: `daily_update.py`, `bulk_update.py`

---

### stock_indicators

**Purpose**: KR 주식 일봉 기술지표 (long-form EAV)

```sql
CREATE TABLE stock_indicators (
  symbol        VARCHAR(32) NOT NULL,
  date          DATE        NOT NULL,
  indicator     VARCHAR(64) NOT NULL,      -- e.g., sma_50_close, sma_200_close
  params_hash   CHAR(40)    NOT NULL,
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

**Indexes**:
- `idx_indicator_date`: `(indicator, date)` — 지표별 시계열 조회
- `idx_symbol_date`: `(symbol, date)` — 종목별 지표 조회
- `idx_indicator_date_market_symbol`: `(indicator, date, market, symbol)` — 지표+일자+시장 조건 및 심볼 조인 조회 최적화

**Config Key**: `indicators` | **Indicators**: SMA(50,100,150,200), IBD RS Rating, RS Line, Blue Dot

---

### kr_sector_snapshot

**Purpose**: KR 섹터/시장 기준 스냅샷 (일별 집계, Grafana 등에서 참조용)

> **Status (running DB, 2026-05-07)**: 테이블 존재. `apps/ingest-databatcher/ops/shell/refresh_kr_sector_snapshot.sh`로 갱신.

```sql
CREATE TABLE kr_sector_snapshot (
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
```

**Primary Key**: `(date, market, symbol)`

**Indexes**:
- `idx_date_market_sector`: `(date, market, sector)` — 일자/시장/섹터 조회 최적화
- `idx_date_market_sector_pass`: `(date, market, sector, is_pass)` — 통과 여부 필터 조회 최적화

---

## KR Stock Weekly Tables

### stock_prices_weekly

**Purpose**: KR 주식 주봉 OHLCV (일봉 집계)

```sql
CREATE TABLE stock_prices_weekly (
  symbol        VARCHAR(32)  NOT NULL,
  week_start    DATE         NOT NULL,
  week_end      DATE         NOT NULL,
  open          DECIMAL(18,4),
  high          DECIMAL(18,4),
  low           DECIMAL(18,4),
  close         DECIMAL(18,4),
  adj_close     DECIMAL(18,4) NULL,
  volume        BIGINT,
  market        VARCHAR(16) NOT NULL,
  source        VARCHAR(16) NOT NULL,
  etl_loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (symbol, week_start),
  KEY idx_week_start (week_start),
  KEY idx_market_week (market, week_start)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**Data Source**: `stock_prices` 집계 | **Update Script**: `weekly_update.py`, `bulk_update_weekly.py`

---

### stock_indicators_weekly

**Purpose**: KR 주식 주봉 기술지표 (long-form EAV)

```sql
CREATE TABLE stock_indicators_weekly (
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
```

**Config Key**: `indicators_weekly` | **Indicators**: SMA(20,50,100,200), EMA(21)

---

## KR Index Tables

### kr_index_master

**Purpose**: KR 지수 마스터 (KOSPI 1001, KOSDAQ 2001)

```sql
CREATE TABLE kr_index_master (
  symbol        VARCHAR(32) PRIMARY KEY,        -- '1001', '2001'
  market        VARCHAR(16) NOT NULL,           -- KOSPI / KOSDAQ
  name          VARCHAR(128) NULL,              -- '코스피', '코스닥'
  status        VARCHAR(16) NOT NULL DEFAULT 'ACTIVE',
  etl_loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**Data Source**: pykrx | **Update Script**: `kr_index_sync_master.py`

---

### kr_index_prices

**Purpose**: KR 지수 일봉 OHLCV (**adj_close 없음**)

```sql
CREATE TABLE kr_index_prices (
  symbol        VARCHAR(32)  NOT NULL,
  date          DATE         NOT NULL,
  open          DECIMAL(18,4),
  high          DECIMAL(18,4),
  low           DECIMAL(18,4),
  close         DECIMAL(18,4),
  volume        BIGINT,
  market        VARCHAR(16) NOT NULL,           -- KOSPI / KOSDAQ
  source        VARCHAR(16) NOT NULL,           -- pykrx / yfinance
  etl_loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (symbol, date),
  KEY idx_date (date),
  KEY idx_market_date (market, date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**Data Source**: `kr_index_daily_update.py`는 pykrx(KRX 로그인) 우선, 실패 시 yfinance fallback / `kr_index_bulk_update.py`는 yfinance | **Update Script**: `kr_index_daily_update.py`, `kr_index_bulk_update.py`

---

### kr_index_indicators

**Purpose**: KR 지수 일봉 기술지표

```sql
CREATE TABLE kr_index_indicators (
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

**Config Key**: `indicators_kr_index` | **Indicators**: SMA(50,100,150,200)

---

## KR Index Weekly Tables

### kr_index_prices_weekly

**Purpose**: KR 지수 주봉 OHLCV (**adj_close 없음**)

```sql
CREATE TABLE kr_index_prices_weekly (
  symbol        VARCHAR(32)  NOT NULL,
  week_start    DATE         NOT NULL,
  week_end      DATE         NOT NULL,
  open          DECIMAL(18,4),
  high          DECIMAL(18,4),
  low           DECIMAL(18,4),
  close         DECIMAL(18,4),
  volume        BIGINT,
  market        VARCHAR(16) NOT NULL,
  source        VARCHAR(16) NOT NULL,
  etl_loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (symbol, week_start),
  KEY idx_week_start (week_start),
  KEY idx_market_week (market, week_start)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**Data Source**: `kr_index_prices` 집계 | **Update Script**: `kr_index_weekly_update.py`, `kr_index_bulk_update_weekly.py`

---

### kr_index_indicators_weekly

**Purpose**: KR 지수 주봉 기술지표

```sql
CREATE TABLE kr_index_indicators_weekly (
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
```

**Config Key**: `indicators_kr_index_weekly` | **Indicators**: SMA(20,50,100,200), EMA(21)

---

## US Stock Tables

### us_symbol_master

**Purpose**: US 주식 마스터 (NYSE/NASDAQ/ETF)

```sql
CREATE TABLE us_symbol_master (
  symbol        VARCHAR(32) PRIMARY KEY,
  market        VARCHAR(16) NOT NULL,          -- NYSE / NASDAQ / ETF
  symbol_type   VARCHAR(16) NULL,              -- STOCK / ETF
  name          VARCHAR(256) NULL,
  status        VARCHAR(16) NOT NULL,          -- ACTIVE / DELISTED
  sector        VARCHAR(128) NULL,             -- Sector (yfinance)
  industry      VARCHAR(128) NULL,             -- Industry (FDR / yfinance)
  sector_source VARCHAR(32) NULL,              -- fdr / yfinance / fdr+yfinance
  sector_updated_at TIMESTAMP NULL,
  etl_loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| symbol | VARCHAR(32) | Ticker symbol (PK) | `AAPL`, `MSFT` |
| market | VARCHAR(16) | Exchange market | `NYSE`, `NASDAQ`, `ETF` |
| symbol_type | VARCHAR(16) | Symbol type | `STOCK`, `ETF` |
| name | VARCHAR(256) | Company name | `Apple Inc.` |
| status | VARCHAR(16) | Listing status | `ACTIVE`, `DELISTED` |
| sector | VARCHAR(128) | Sector (yfinance) | `Technology`, `Healthcare` |
| industry | VARCHAR(128) | Industry (FDR/yfinance) | `Consumer Electronics` |
| sector_source | VARCHAR(32) | Sector data source | `fdr`, `yfinance`, `fdr+yfinance` |
| sector_updated_at | TIMESTAMP | Sector info updated at | `2026-02-08 12:00:00` |

**Data Source**: FinanceDataReader + yfinance | **Update Script**: `us_sync_symbol_master.py`

---

### us_stock_prices

**Purpose**: US 주식 일봉 OHLCV

```sql
CREATE TABLE us_stock_prices (
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
```

**Data Source**: FinanceDataReader | **Update Script**: `us_daily_update.py`, `us_bulk_update.py`

---

### us_stock_indicators

**Purpose**: US 주식 일봉 기술지표

```sql
CREATE TABLE us_stock_indicators (
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

**Config Key**: `indicators_us` | **Indicators**: SMA(50,100,150,200), IBD RS Rating, RS Line, Blue Dot

---

## US Stock Weekly Tables

### us_stock_prices_weekly

**Purpose**: US 주식 주봉 OHLCV (일봉 집계)

```sql
CREATE TABLE us_stock_prices_weekly (
  symbol        VARCHAR(32)  NOT NULL,
  week_start    DATE         NOT NULL,
  week_end      DATE         NOT NULL,
  open          DECIMAL(18,4),
  high          DECIMAL(18,4),
  low           DECIMAL(18,4),
  close         DECIMAL(18,4),
  adj_close     DECIMAL(18,4) NULL,
  volume        BIGINT,
  market        VARCHAR(16) NOT NULL,
  source        VARCHAR(16) NOT NULL,
  etl_loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (symbol, week_start),
  KEY idx_week_start (week_start),
  KEY idx_market_week (market, week_start)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**Data Source**: `us_stock_prices` 집계 | **Update Script**: `us_weekly_update.py`, `us_bulk_update_weekly.py`

---

### us_stock_indicators_weekly

**Purpose**: US 주식 주봉 기술지표

```sql
CREATE TABLE us_stock_indicators_weekly (
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
```

**Config Key**: `indicators_us_weekly` | **Indicators**: SMA(20,50,100,200), EMA(21)

---

## US Index Tables

### us_index_master

**Purpose**: US 지수 마스터 (S&P 500, Dow Jones, NASDAQ Composite)

```sql
CREATE TABLE us_index_master (
  symbol        VARCHAR(32) PRIMARY KEY,        -- 'US500', 'DJI', 'IXIC'
  market        VARCHAR(16) NOT NULL,           -- SP500 / DJI / IXIC
  name          VARCHAR(128) NULL,
  status        VARCHAR(16) NOT NULL DEFAULT 'ACTIVE',
  etl_loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**Data Source**: Hardcoded | **Update Script**: `us_index_sync_master.py`

---

### us_index_prices

**Purpose**: US 지수 일봉 OHLCV (**adj_close 없음**)

```sql
CREATE TABLE us_index_prices (
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
```

**Data Source**: FinanceDataReader | **Update Script**: `us_index_daily_update.py`, `us_index_bulk_update.py`

---

### us_index_indicators

**Purpose**: US 지수 일봉 기술지표

```sql
CREATE TABLE us_index_indicators (
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

**Config Key**: `indicators_us_index` | **Indicators**: SMA(50,100,150,200)

---

## US Index Weekly Tables

### us_index_prices_weekly

**Purpose**: US 지수 주봉 OHLCV (**adj_close 없음**)

```sql
CREATE TABLE us_index_prices_weekly (
  symbol        VARCHAR(32)  NOT NULL,
  week_start    DATE         NOT NULL,
  week_end      DATE         NOT NULL,
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
```

**Data Source**: `us_index_prices` 집계 | **Update Script**: `us_index_weekly_update.py`, `us_index_bulk_update_weekly.py`

---

### us_index_indicators_weekly

**Purpose**: US 지수 주봉 기술지표

```sql
CREATE TABLE us_index_indicators_weekly (
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
```

**Config Key**: `indicators_us_index_weekly` | **Indicators**: SMA(20,50,100,200), EMA(21)

---

## Crypto Tables

### crypto_symbol_master

**Purpose**: Binance 거래쌍 마스터 (USDT)

```sql
CREATE TABLE crypto_symbol_master (
  symbol        VARCHAR(32)  NOT NULL,     -- e.g., BTCUSDT
  base_asset    VARCHAR(16)  NOT NULL,     -- e.g., BTC
  quote_asset   VARCHAR(16)  NOT NULL,     -- e.g., USDT
  status        VARCHAR(16)  NOT NULL,     -- ACTIVE / INACTIVE
  exchange      VARCHAR(16)  NOT NULL,     -- BINANCE
  etl_loaded_at TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (symbol),
  KEY idx_quote_status (quote_asset, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**Data Source**: Binance API | **Update Script**: `crypto_sync_symbol_master.py`

---

### crypto_prices_daily

**Purpose**: Crypto 일봉 OHLCV (UTC 기준, `volume_quote` 사용)

```sql
CREATE TABLE crypto_prices_daily (
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
```

> **Note**: Crypto 테이블은 `market`/`source` 대신 `exchange`/`source` 컬럼 사용. 가격 정밀도가 DECIMAL(28,10)으로 주식(18,4)보다 높음.

---

### crypto_indicators_daily

**Purpose**: Crypto 일봉 기술지표

```sql
CREATE TABLE crypto_indicators_daily (
  symbol        VARCHAR(32) NOT NULL,
  date          DATE        NOT NULL,
  indicator     VARCHAR(64) NOT NULL,
  params_hash   CHAR(40)    NOT NULL,
  value         DECIMAL(28,10) NULL,
  exchange      VARCHAR(16) NOT NULL,
  source        VARCHAR(16) NOT NULL,
  etl_loaded_at TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (symbol, date, indicator, params_hash),
  KEY idx_indicator_date (indicator, date),
  KEY idx_symbol_date (symbol, date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**Config Key**: `indicators_crypto_daily` | **Indicators**: SMA(50,100,150,200)

---

## Crypto Weekly Tables

### crypto_prices_weekly

**Purpose**: Crypto 주봉 OHLCV (일봉 집계)

```sql
CREATE TABLE crypto_prices_weekly (
  symbol        VARCHAR(32)  NOT NULL,
  week_start    DATE         NOT NULL,     -- UTC Monday
  week_end      DATE         NOT NULL,     -- UTC Sunday
  open          DECIMAL(28,10) NULL,
  high          DECIMAL(28,10) NULL,
  low           DECIMAL(28,10) NULL,
  close         DECIMAL(28,10) NULL,
  volume_quote  DECIMAL(28,10) NULL,
  exchange      VARCHAR(16)  NOT NULL,
  source        VARCHAR(16)  NOT NULL,
  etl_loaded_at TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (symbol, week_start),
  KEY idx_week_start (week_start),
  KEY idx_symbol_week (symbol, week_start)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**Data Source**: `crypto_prices_daily` 집계 | **Update Script**: `crypto_weekly_update.py`, `crypto_bulk_update_weekly.py`

---

### crypto_indicators_weekly

**Purpose**: Crypto 주봉 기술지표

```sql
CREATE TABLE crypto_indicators_weekly (
  symbol        VARCHAR(32) NOT NULL,
  week_start    DATE        NOT NULL,
  indicator     VARCHAR(64) NOT NULL,
  params_hash   CHAR(40)    NOT NULL,
  value         DECIMAL(28,10) NULL,
  exchange      VARCHAR(16) NOT NULL,
  source        VARCHAR(16) NOT NULL,
  etl_loaded_at TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (symbol, week_start, indicator, params_hash),
  KEY idx_indicator_week (indicator, week_start),
  KEY idx_symbol_week (symbol, week_start)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**Config Key**: `indicators_crypto_weekly` | **Indicators**: SMA(20,50,100,200)

---

## Minervini Screen Tables

### minervini_screen_results_kr

**Purpose**: 미너비니 트렌드 템플릿 스크리닝 결과 (한국 주식)

```sql
CREATE TABLE minervini_screen_results_kr (
  symbol             VARCHAR(32)  NOT NULL,
  date               DATE         NOT NULL,
  market             VARCHAR(16)  NOT NULL,      -- KOSPI / KOSDAQ / ETF
  rs_rating          DECIMAL(5,1) NULL,
  is_blue_dot        TINYINT      NULL,
  conditions_met     JSON         NULL,           -- ADR-009 (P0.5 추가): per-condition pass/fail map
  screen_config_hash CHAR(40)     NOT NULL,
  failed_reason      VARCHAR(512) NULL,
  created_at         TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (symbol, date, screen_config_hash),
  KEY idx_date_market_config (date, market, screen_config_hash),
  KEY idx_date_market_symbol (date, market, symbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| symbol | VARCHAR(32) | 종목 코드 (PK) | `005930` |
| date | DATE | 스크리닝 날짜 (PK) | `2026-02-07` |
| market | VARCHAR(16) | 시장 구분 | `KOSPI`, `KOSDAQ`, `ETF` |
| rs_rating | DECIMAL(5,1) | IBD RS Rating (1~99) | `85.2` |
| is_blue_dot | TINYINT | Blue Dot 신호 (0/1) | `1` |
| conditions_met | JSON | 미너비니 8조건 통과 여부 (ADR-009) | `{"price_above_ma150_ma200": true, ...}` |
| screen_config_hash | CHAR(40) | 스크리닝 설정 해시 (PK) | `abc123...` |
| failed_reason | VARCHAR(512) | 탈락 사유 (미사용, NULL) | NULL |
| created_at | TIMESTAMP | 레코드 생성 시각 | `2026-02-07 17:00:00` |

**Primary Key**: `(symbol, date, screen_config_hash)`

**Indexes**:
- `idx_date_market_config`: `(date, market, screen_config_hash)` — 날짜별 조회 최적화
- `idx_date_market_symbol`: `(date, market, symbol)` — 날짜/시장 기준 종목 조인 최적화

**Storage**: 통과 종목만 저장 (탈락 종목은 저장하지 않음)

**`conditions_met` JSON 키** (8개, ADR-009 / `_meta/05_GLOSSARY.md` Part B.2):
```
price_above_ma150_ma200, ma150_above_ma200, ma200_uptrend_1mo,
ma50_above_ma150_ma200, price_above_ma50, price_30pct_above_52w_low,
price_within_25pct_of_52w_high, rs_rating_above_70
```

**Config Key**: `minervini_kr`

**Related Scripts**:
- `scripts/kr_minervini_update.py` — 스크리닝 배치 실행 (ADR-013 ETF 제외 적용)

---

### minervini_screen_results_us

**Purpose**: 미너비니 트렌드 템플릿 스크리닝 결과 (미국 주식)

```sql
CREATE TABLE minervini_screen_results_us (
  symbol             VARCHAR(32)  NOT NULL,
  date               DATE         NOT NULL,
  market             VARCHAR(16)  NOT NULL,      -- NYSE / NASDAQ / ETF
  rs_rating          DECIMAL(5,1) NULL,
  is_blue_dot        TINYINT      NULL,
  conditions_met     JSON         NULL,           -- ADR-009 (P0.5 추가): per-condition pass/fail map
  screen_config_hash CHAR(40)     NOT NULL,
  failed_reason      VARCHAR(512) NULL,
  created_at         TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (symbol, date, screen_config_hash),
  KEY idx_date_market_config (date, market, screen_config_hash)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| symbol | VARCHAR(32) | 종목 코드 (PK) | `AAPL` |
| date | DATE | 스크리닝 날짜 (PK) | `2026-02-07` |
| market | VARCHAR(16) | 시장 구분 | `NYSE`, `NASDAQ`, `ETF` |
| rs_rating | DECIMAL(5,1) | IBD RS Rating (1~99) | `92.5` |
| is_blue_dot | TINYINT | Blue Dot 신호 (0/1) | `1` |
| conditions_met | JSON | 미너비니 8조건 통과 여부 (ADR-009) | (KR과 동일 8키) |
| screen_config_hash | CHAR(40) | 스크리닝 설정 해시 (PK) | `abc123...` |
| failed_reason | VARCHAR(512) | 탈락 사유 (미사용, NULL) | NULL |
| created_at | TIMESTAMP | 레코드 생성 시각 | `2026-02-07 07:00:00` |

**Primary Key**: `(symbol, date, screen_config_hash)`

**Indexes**:
- `idx_date_market_config`: `(date, market, screen_config_hash)` — 날짜별 조회 최적화

**Storage**: 통과 종목만 저장 (탈락 종목은 저장하지 않음)

**Config Key**: `minervini_us`

**Related Scripts**:
- `scripts/us_minervini_update.py` — 스크리닝 배치 실행 (ADR-013 ETF 제외 적용)

---

## LLM Analysis Tables

> Phase 1 (ADR-009)에서 신설. 미너비니 통과 종목에 대해 LLM이 차트 분석·분류와 진입 파라미터를 산출한다.
> 헌법 §2.2 준수: `apps/llm-analysis/`는 `apps/ingest-databatcher/` 함수를 import하지 않으며 본 테이블들을 통해 DB 레벨로만 연결된다.

### daily_analysis_kr

**Purpose**: KR 주식 일일 LLM 분석 결과 (5) `analyze_chart` + (6) `calculate_entry_params`

```sql
CREATE TABLE daily_analysis_kr (
  symbol             VARCHAR(32)  NOT NULL,
  date               DATE         NOT NULL,
  market             VARCHAR(16)  NOT NULL,      -- KOSPI / KOSDAQ / ETF
  classification     VARCHAR(20)  NOT NULL,      -- entry / watch / ignore
  confidence         DECIMAL(3,2) NULL,          -- 0.00 ~ 1.00
  reasoning          TEXT         NULL,          -- LLM 자연어 근거
  pattern            VARCHAR(50)  NULL,          -- VCP / flat_base / cup_handle / 3c_cheat / double_bottom / none
  risk_flags         JSON         NULL,          -- 12개 화이트리스트 (Phase 1.1.15 v2)
  entry_params       JSON         NULL,          -- v1.1 16필드 (Phase 1.3.0)
  screen_config_hash CHAR(40)     NULL,
  llm_call_id        BIGINT       NULL,          -- llm_calls.id 소프트 외래키
  created_at         TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (symbol, date),
  KEY idx_date_class (date, classification),
  KEY idx_date_market (date, market)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**Primary Key**: `(symbol, date)` — KR/US 분리이므로 region 컬럼 불필요 (ADR-009)

**JSON 스키마**: `_meta/05_GLOSSARY.md` Part B.2 참조 (`risk_flags` 12 whitelist + `entry_params` v1.1 16필드)

**Related Scripts** (Phase 1.3):
- `apps/llm-analysis/scripts/run_daily_analysis.py --region KR` — 일일 배치 진입점
- `apps/llm-analysis/scripts/run_single_symbol.py --region KR` — 단일 종목 디버깅
- `apps/llm-analysis/scripts/show_cost_summary.py` — 호출 통계 점검

---

### daily_analysis_us

**Purpose**: US 주식 일일 LLM 분석 결과. `daily_analysis_kr`와 구조 동일, `market` 값만 NYSE/NASDAQ/ETF.

```sql
CREATE TABLE daily_analysis_us (
  symbol             VARCHAR(32)  NOT NULL,
  date               DATE         NOT NULL,
  market             VARCHAR(16)  NOT NULL,      -- NYSE / NASDAQ / ETF
  classification     VARCHAR(20)  NOT NULL,
  confidence         DECIMAL(3,2) NULL,
  reasoning          TEXT         NULL,
  pattern            VARCHAR(50)  NULL,
  risk_flags         JSON         NULL,
  entry_params       JSON         NULL,
  screen_config_hash CHAR(40)     NULL,
  llm_call_id        BIGINT       NULL,
  created_at         TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (symbol, date),
  KEY idx_date_class (date, classification),
  KEY idx_date_market (date, market)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

### llm_calls

**Purpose**: 모든 LLM 호출의 영구 보존 (헌법 §2.5 — "모든 LLM 출력은 구조화된 형식으로 저장")

```sql
CREATE TABLE llm_calls (
  id                BIGINT PRIMARY KEY AUTO_INCREMENT,
  timestamp         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  module            VARCHAR(50),                  -- analysis_5_kr | analysis_5_us | entry_params_6_kr | entry_params_6_us | agent_8 ...
  model             VARCHAR(50),                  -- claude-sonnet-4-5 등
  prompt_tokens     INT,
  completion_tokens INT,
  cost_usd          DECIMAL(10,6),                -- CLI 백엔드는 NULL 또는 참고값 (ADR-011 §3)
  request_payload   JSON,
  response_payload  JSON,
  duration_ms       INT,
  error             TEXT NULL,
  KEY idx_timestamp (timestamp),
  KEY idx_module_timestamp (module, timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**용도**:
- 사후 검증·디버깅·통계 (헌법 §2.5)
- ADR-012 §3.4 호출 로그 주간 점검 (`show_cost_summary.py`)
- ADR-012 §3.1 일일 호출 상한 카운트 source

---

## Auth & User Tables

### users

**Purpose**: 트레이딩 뷰 프로젝트(`apps/trading-view-project/`) 인증 사용자 마스터

```sql
CREATE TABLE users (
  id                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  username            VARCHAR(64)  NOT NULL,
  password_hash       VARCHAR(255) NOT NULL,
  role                VARCHAR(16)  NOT NULL DEFAULT 'viewer',  -- viewer | editor (CHECK constraint)
  is_active           TINYINT(1)   NOT NULL DEFAULT 1,
  created_at          DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at          DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  last_login_at       DATETIME     NULL,
  failed_login_count  INT UNSIGNED NOT NULL DEFAULT 0,
  locked_until        DATETIME     NULL,
  password_changed_at DATETIME     NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_users_username (username),
  CONSTRAINT chk_user_role CHECK (role IN ('viewer','editor'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**Used by**: `apps/trading-view-project/` (FastAPI auth + frontend login)

---

### minervini_list_selection

**Purpose**: 미너비니 통과 종목에 대한 사용자 분류 상태 (focus / action / pass) — 진입 후보 picking 워크플로

```sql
CREATE TABLE minervini_list_selection (
  id           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  region       VARCHAR(8)   NOT NULL,           -- KR | US (CHECK 미적용, 코드 enforce)
  date         DATE         NOT NULL,
  market       VARCHAR(32)  NOT NULL,
  symbol       VARCHAR(32)  NOT NULL,
  list_type    VARCHAR(16)  NOT NULL,           -- focus | action | pass (CHECK constraint)
  trigger_price DECIMAL(18,4) NULL,             -- ≥ 0 (CHECK)
  stop_price    DECIMAL(18,4) NULL,             -- ≥ 0 (CHECK)
  status_tag   VARCHAR(32)  NULL,               -- A | B | C | D | E
  memo         TEXT NULL,
  updated_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_minervini_list_selection (region, date, market, symbol),
  KEY idx_minervini_list_selection_lookup (region, date, list_type),
  CONSTRAINT chk_minervini_list_type CHECK (list_type IN ('focus','action','pass')),
  CONSTRAINT chk_trigger_price_nonneg CHECK (trigger_price IS NULL OR trigger_price >= 0),
  CONSTRAINT chk_stop_price_nonneg    CHECK (stop_price    IS NULL OR stop_price    >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**Used by**: `apps/trading-view-project/` (사용자가 차트에서 진입 트리거·손절 설정)

**Note**: Phase 6에서 `order_reservations`와의 관계 정리 + `watchlist_items`(legacy)와 통합 검토 예정.

---

## System Tables

### sync_log

**Purpose**: ETL 작업 실행 로그 + LLM 분석 모니터링 이벤트 (ADR-012 §3.2)

```sql
CREATE TABLE sync_log (
  id            BIGINT AUTO_INCREMENT PRIMARY KEY,
  job_name      VARCHAR(64) NOT NULL,
  market        VARCHAR(16) NOT NULL,
  symbol        VARCHAR(32) NULL,
  start_time    DATETIME NOT NULL,
  end_time      DATETIME NULL,
  rows_processed INT DEFAULT 0,
  status        VARCHAR(16) NOT NULL,      -- success / failed / running / WARN / ERROR
  message       VARCHAR(1024) NULL,
  created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_job_market_time (job_name, market, start_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**Active jobs (status 값)**:
- ETL 적재(`success`/`failed`/`running`) — Phase 0 이후 사용
- LLM 분석 모니터링(`WARN`/`ERROR`) — Phase 1.3.2부터 사용:
  - `llm_analysis_kr` / `llm_analysis_us` — 일일 분석 배치 마커
  - `llm_daily_call_limit` — 일일 호출 한도 도달 (ADR-012 §3.1)
  - `llm_terms_violation_signal` — 약관 위반 징후 패턴 매치 (ADR-012 §3.3)
  - `llm_token_spike` — 프롬프트 토큰 폭증 감지 (1.1.7 후속, ADR-012 §3.2)

---

### alembic_version

**Purpose**: Alembic 마이그레이션 버전 트래커

```sql
CREATE TABLE alembic_version (
  version_num VARCHAR(32) NOT NULL,
  PRIMARY KEY (version_num)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**State (DEV, 2026-05-07)**: head = `20260424_000001` (P0.5 시점 stamp). Phase 1 마이그레이션(`20260428_000001_add_daily_analysis_and_llm_calls`)은 raw SQL 직접 적용 — DEV·PROD `alembic_version` 동기화는 미해결 이슈 §G로 추적 중 (`_meta/06_CURRENT_STATE.md`).

---

### watchlist_items

**Purpose**: 사용자별 관심 종목(legacy, 미사용)

> **Status**: 본 테이블은 과거 설계의 잔존 테이블. 현재 로직에서 호출되지 않으며, Phase 6에서 `order_reservations` 설계 시 `minervini_list_selection`과 통합 또는 제거 결정 예정.

```sql
CREATE TABLE watchlist_items (
  id           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id      BIGINT UNSIGNED NOT NULL,
  user_login   VARCHAR(190) NULL,
  market       VARCHAR(8) NOT NULL,               -- 'KR' / 'US'
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
```

---

## Database Views

### KR Stock Views

| View | Source Tables | Pivot Indicators |
|------|-------------|-----------------|
| `v_stock_price_with_ma` | `stock_prices` + `stock_indicators` | SMA(50,100,150,200), RS Line |
| `v_stock_price_weekly_with_ma` | `stock_prices_weekly` + `stock_indicators_weekly` | SMA(20,50,100,200), EMA(21) |

### KR Index Views

| View | Source Tables | Pivot Indicators |
|------|-------------|-----------------|
| `v_kr_index_price_with_ma` | `kr_index_prices` + `kr_index_indicators` | SMA(50,100,150,200) |
| `v_kr_index_price_weekly_with_ma` | `kr_index_prices_weekly` + `kr_index_indicators_weekly` | SMA(5,20)\*, EMA(12,26)\* |

### US Stock Views

| View | Source Tables | Pivot Indicators |
|------|-------------|-----------------|
| `v_us_stock_price_with_ma` | `us_stock_prices` + `us_stock_indicators` | SMA(50,100,150,200), RS Line |
| `v_us_stock_price_weekly_with_ma` | `us_stock_prices_weekly` + `us_stock_indicators_weekly` | SMA(20,50,100,200), EMA(21) |

### US Index Views

| View | Source Tables | Pivot Indicators |
|------|-------------|-----------------|
| `v_us_index_price_with_ma` | `us_index_prices` + `us_index_indicators` | SMA(50,100,150,200) |
| `v_us_index_price_weekly_with_ma` | `us_index_prices_weekly` + `us_index_indicators_weekly` | SMA(5,20,40)\* |

### Crypto Views

| View | Source Tables | Pivot Indicators |
|------|-------------|-----------------|
| `v_crypto_price_weekly_with_ma` | `crypto_prices_weekly` + `crypto_indicators_weekly` | SMA(20,50,100,200), EMA(21) |

### Watchlist Views

| View | Source Tables | Pivot/Join Columns |
|------|-------------|--------------------|
| `v_watchlist_items_kr` | `watchlist_items` + `symbol_master` | watchlist columns + `name`, `kr_market`, `sector`, `industry` |

> **\* View/Pipeline 불일치 주의**: 일부 주봉 뷰의 PIVOT 컬럼이 현재 지표 적재 패턴과 달라 NULL 비율이 높을 수 있습니다.

**Usage Example**:
```sql
-- KR 주식: 삼성전자 일봉 + 이동평균
SELECT * FROM v_stock_price_with_ma WHERE symbol = '005930' AND date >= '2024-01-01' ORDER BY date DESC;

-- US 주식: Apple 일봉 + 이동평균
SELECT * FROM v_us_stock_price_with_ma WHERE symbol = 'AAPL' AND date >= '2024-01-01' ORDER BY date DESC;

-- US 지수: S&P 500 일봉 + 이동평균
SELECT * FROM v_us_index_price_with_ma WHERE symbol = 'US500' AND date >= '2024-01-01' ORDER BY date DESC;

-- Crypto: 비트코인 주봉 + 이동평균
SELECT * FROM v_crypto_price_weekly_with_ma WHERE symbol = 'BTCUSDT' ORDER BY week_start DESC LIMIT 10;
```

---

## Scripts and Tables Mapping

### KR Stock

| Script | Reads From | Writes To | Frequency |
|--------|-----------|-----------|-----------|
| `sync_symbol_master.py` | pykrx API | `symbol_master` | Weekly |
| `bulk_update.py` | pykrx API, `symbol_master` | `stock_prices`, `stock_indicators` | Initial |
| `daily_update.py` | pykrx API, `symbol_master`, `stock_prices` | `stock_prices`, `stock_indicators` | Daily |
| `bulk_update_weekly.py` | `stock_prices` | `stock_prices_weekly`, `stock_indicators_weekly` | Initial |
| `weekly_update.py` | `stock_prices` | `stock_prices_weekly`, `stock_indicators_weekly` | Weekly |
| `kr_rs_update.py` | `stock_prices`, `kr_index_prices` | `stock_indicators` | Daily |
| `kr_minervini_update.py` | `stock_prices`, `stock_indicators` | `minervini_screen_results_kr` | Daily |

### KR Index

| Script | Reads From | Writes To | Frequency |
|--------|-----------|-----------|-----------|
| `kr_index_sync_master.py` | pykrx API | `kr_index_master` | Weekly |
| `kr_index_bulk_update.py` | pykrx API, `kr_index_master` | `kr_index_prices`, `kr_index_indicators` | Initial |
| `kr_index_daily_update.py` | pykrx API (KRX 로그인) 우선, 실패 시 yfinance fallback, `kr_index_prices` | `kr_index_prices`, `kr_index_indicators` | Daily |
| `kr_index_bulk_update_weekly.py` | `kr_index_prices` | `kr_index_prices_weekly`, `kr_index_indicators_weekly` | Initial |
| `kr_index_weekly_update.py` | `kr_index_prices` | `kr_index_prices_weekly`, `kr_index_indicators_weekly` | Weekly |

### US Stock

| Script | Reads From | Writes To | Frequency |
|--------|-----------|-----------|-----------|
| `us_sync_symbol_master.py` | FDR API | `us_symbol_master` | Weekly |
| `us_bulk_update.py` | FDR API, `us_symbol_master` | `us_stock_prices`, `us_stock_indicators` | Initial |
| `us_daily_update.py` | FDR API, `us_symbol_master`, `us_stock_prices` | `us_stock_prices`, `us_stock_indicators` | Daily |
| `us_bulk_update_weekly.py` | `us_stock_prices` | `us_stock_prices_weekly`, `us_stock_indicators_weekly` | Initial |
| `us_weekly_update.py` | `us_stock_prices` | `us_stock_prices_weekly`, `us_stock_indicators_weekly` | Weekly |
| `us_rs_update.py` | `us_stock_prices`, `us_index_prices` | `us_stock_indicators` | Daily |
| `us_minervini_update.py` | `us_stock_prices`, `us_stock_indicators` | `minervini_screen_results_us` | Daily |

### US Index

| Script | Reads From | Writes To | Frequency |
|--------|-----------|-----------|-----------|
| `us_index_sync_master.py` | Hardcoded | `us_index_master` | Weekly |
| `us_index_bulk_update.py` | FDR API, `us_index_master` | `us_index_prices`, `us_index_indicators` | Initial |
| `us_index_daily_update.py` | FDR API, `us_index_prices` | `us_index_prices`, `us_index_indicators` | Daily |
| `us_index_bulk_update_weekly.py` | `us_index_prices` | `us_index_prices_weekly`, `us_index_indicators_weekly` | Initial |
| `us_index_weekly_update.py` | `us_index_prices` | `us_index_prices_weekly`, `us_index_indicators_weekly` | Weekly |

### Crypto

| Script | Reads From | Writes To | Frequency |
|--------|-----------|-----------|-----------|
| `crypto_sync_symbol_master.py` | Binance API | `crypto_symbol_master` | Weekly |
| `crypto_bulk_update.py` | Binance API | `crypto_prices_daily`, `crypto_indicators_daily` | Initial |
| `crypto_daily_update.py` | Binance API | `crypto_prices_daily`, `crypto_indicators_daily` | Daily |
| `crypto_bulk_update_weekly.py` | `crypto_prices_daily` | `crypto_prices_weekly`, `crypto_indicators_weekly` | Initial |
| `crypto_weekly_update.py` | `crypto_prices_daily` | `crypto_prices_weekly`, `crypto_indicators_weekly` | Weekly |

### LLM Analysis (Phase 1, `apps/llm-analysis/`)

본 앱은 헌법 §2.2에 따라 `apps/ingest-databatcher/` 함수를 import하지 않고 DB만 공유한다.

| Script | Reads From | Writes To | Frequency |
|--------|-----------|-----------|-----------|
| `scripts/run_daily_analysis.py` | `minervini_screen_results_kr/us`, `stock_prices`, `us_stock_prices`, `*_indicators`, `*_symbol_master` | `daily_analysis_kr` 또는 `daily_analysis_us`, `llm_calls`, `sync_log` | Daily (Task Scheduler, ADR-012) |
| `scripts/run_single_symbol.py` | (위와 동일, 단일 종목) | (위와 동일) | On-demand |
| `scripts/show_cost_summary.py` | `llm_calls`, `sync_log` | (read-only) | Weekly check |
| `scripts/backfill_analysis.py` | (위와 동일) | (위와 동일) | On-demand |

**Task Scheduler 등록** (ADR-012, Q-003):
- `LLMAnalysis_US` — 매일 16:00 KST → `ops/scheduler/windows/run_analysis_today.ps1 -Region US`
- `LLMAnalysis_KR` — 매일 21:00 KST → `ops/scheduler/windows/run_analysis_today.ps1 -Region KR`

---

## Index Strategy

### Price Tables (Daily)
```sql
PRIMARY KEY (symbol, date)              -- Point lookup: 특정 종목의 특정 날짜
KEY idx_date (date)                     -- 특정 날짜의 전체 종목 조회
KEY idx_market_date (market, date)      -- 특정 시장 + 날짜 범위 조회
```

### Price Tables (Weekly)
```sql
PRIMARY KEY (symbol, week_start)        -- Point lookup: 특정 종목의 특정 주
KEY idx_week_start (week_start)         -- 특정 주의 전체 종목 조회
KEY idx_market_week (market, week_start) -- 특정 시장 + 주 범위 조회
```

### Indicator Tables
```sql
PRIMARY KEY (symbol, date|week_start, indicator, params_hash) -- 동일 지표 다중 파라미터 지원
KEY idx_indicator_date|week (indicator, date|week_start)      -- 지표별 시계열 분석
KEY idx_symbol_date|week (symbol, date|week_start)            -- 종목별 전체 지표 조회
KEY idx_indicator_date_market_symbol (indicator, date, market, symbol) -- KR 일봉 지표 복합 필터 최적화
```

### Crypto-specific
```sql
-- crypto_symbol_master
KEY idx_quote_status (quote_asset, status)  -- USDT + ACTIVE 필터링
```

---

## Data Types and Precision

| Type | Usage | Range | Example |
|------|-------|-------|---------|
| `DECIMAL(18,4)` | 주식/지수 가격 | ~14자리 정수 + 4자리 소수 | `71234.5678` |
| `DECIMAL(28,10)` | Crypto 가격, 지표 값 | ~18자리 정수 + 10자리 소수 | `0.0000012345` |
| `BIGINT` | 거래량 | ~9.2 × 10^18 | `17142847` |
| `CHAR(40)` | params_hash (SHA1) | 40 hex chars | `e1263f1c0f1d...` |
| `VARCHAR(32)` | symbol | Max 32 chars | `005930`, `BTCUSDT` |
| `VARCHAR(64)` | indicator name | Max 64 chars | `sma_20_close` |
| `VARCHAR(16)` | market, source, status | Max 16 chars | `KOSPI`, `fdr` |

### Indicator Naming Convention
- Format: `{indicator}_{window}_{column}`
- Examples: `sma_50_close`, `sma_200_close`, `ema_21_close`

---

## Character Encoding

```sql
DEFAULT CHARSET=utf8mb4
```

- Korean: `삼성전자`, `SK하이닉스`
- Full Unicode range
- Connection string: `?charset=utf8mb4`
