# DataBatcher DB Data Catalog

**Last Updated**: 2026-02-26
**Database**: MySQL 8.0 (InnoDB, utf8mb4)
**Total**: 30 tables (25 data + 2 screening + 2 system + 1 utility) + 10 views

---

## Table of Contents

1. [Overview & Purpose](#1-overview--purpose)
2. [Master Tables (5)](#2-master-tables)
3. [Price Tables (10)](#3-price-tables)
4. [Indicator Tables (10)](#4-indicator-tables)
5. [Screening & Utility Tables (3)](#5-screening--utility-tables)
6. [Database Views (10)](#6-database-views)
7. [Indicator Storage Pattern](#7-indicator-storage-pattern)
8. [Key Differences Between Asset Classes](#8-key-differences-between-asset-classes)
9. [Sample Queries for Grafana](#9-sample-queries-for-grafana)

---

## 1. Overview & Purpose

DataBatcher is a multi-market stock data warehouse collecting price data and computing technical indicators across 5 asset classes:

| Asset Class | Markets | Date Range | Data Source | Symbols (approx) |
|-------------|---------|------------|-------------|-------------------|
| KR Stock | KOSPI, KOSDAQ, KONEX | 2020-01-01 ~ present | pykrx | ~2,900 |
| KR Index | KOSPI (1001), KOSDAQ (2001) | 2020-01-01 ~ present | pykrx | 2 |
| US Stock | NYSE, NASDAQ, ETF | 2020-01-01 ~ present | FinanceDataReader | ~10,000+ |
| US Index | S&P 500, Dow Jones, NASDAQ Composite | 2020-01-01 ~ present | FinanceDataReader | 3 |
| Crypto | Binance Spot (USDT pairs) | 2017-01-01 ~ present | Binance API | ~500+ |

**Core Pipeline**: Data Collection (collectors) -> Indicator Calculation (indicators) -> Database Storage (MySQL)

Each asset class has: **master table** + **daily price table** + **daily indicator table** + **weekly price table** + **weekly indicator table** = 5 tables per class, totaling 25 data tables + 2 screening tables + 2 system tables (`sync_log`, `metrics`) + 1 utility table (`watchlist_items`).

**Schema status note (real DB 기준)**:
- `watchlist_items` / `v_watchlist_items_kr` are present in the running DB.
- `kr_sector_snapshot` is defined in init SQL/docs but currently not created in the running DB.

---

## 2. Master Tables

### 2.1 `symbol_master` — KR Stock Symbols

| Column | Type | Description | Example Values |
|--------|------|-------------|----------------|
| symbol | VARCHAR(32) PK | KRX stock code | `005930`, `000660` |
| market | VARCHAR(16) | Exchange market | `KOSPI`, `KOSDAQ`, `KONEX`, `ETF` |
| symbol_type | VARCHAR(16) | Symbol type | `STOCK`, `ETF` |
| name | VARCHAR(128) | Company name (Korean) | `삼성전자`, `SK하이닉스` |
| status | VARCHAR(16) | Listing status | `ACTIVE`, `DELISTED` |
| sector | VARCHAR(128) | pykrx 대분류 (26개) | `전기전자`, `서비스업` |
| sector_detail | VARCHAR(256) | FDR 세분류 (162개) | `반도체`, `소프트웨어` |
| industry | VARCHAR(512) | FDR Industry | `반도체와반도체장비` |
| sector_source | VARCHAR(32) | Sector data source | `pykrx+fdr`, `pykrx`, `fdr` |
| sector_updated_at | TIMESTAMP | Sector info updated at | `2026-02-08 12:00:00` |
| first_date | DATE | Earliest data date | NULL (not populated) |
| last_date | DATE | Latest data date | NULL (not populated) |

**Approximate counts**: KOSPI ~950, KOSDAQ ~1,700, KONEX ~100, ETF ~700. Total ~3,500 symbols.
**Sync script**: `scripts/sync_symbol_master.py` (weekly) — pykrx 대분류 + FDR KRX-DESC 세분류 자동 수집

---

### 2.2 `us_symbol_master` — US Stock Symbols

| Column | Type | Description | Example Values |
|--------|------|-------------|----------------|
| symbol | VARCHAR(32) PK | Ticker symbol | `AAPL`, `MSFT`, `SPY` |
| market | VARCHAR(16) | Exchange market | `NYSE`, `NASDAQ`, `ETF` |
| symbol_type | VARCHAR(16) | Symbol type | `STOCK`, `ETF` |
| name | VARCHAR(256) | Company name | `Apple Inc.`, `Microsoft Corp` |
| status | VARCHAR(16) | Listing status | `ACTIVE`, `DELISTED` |
| sector | VARCHAR(128) | Sector (yfinance) | `Technology`, `Healthcare` |
| industry | VARCHAR(128) | Industry (FDR/yfinance) | `Consumer Electronics` |
| sector_source | VARCHAR(32) | Sector data source | `fdr`, `yfinance`, `fdr+yfinance` |
| sector_updated_at | TIMESTAMP | Sector info updated at | `2026-02-08 12:00:00` |

**Approximate counts**: NYSE ~3,500, NASDAQ ~4,500, ETF ~2,500. Total ~10,000+ symbols.
**Sync script**: `scripts/us_sync_symbol_master.py` (weekly) — FDR Industry + yfinance Sector 자동 수집

---

### 2.3 `kr_index_master` — KR Index Symbols

| Column | Type | Description | Example Values |
|--------|------|-------------|----------------|
| symbol | VARCHAR(32) PK | Index code | `1001`, `2001` |
| market | VARCHAR(16) | Index name | `KOSPI`, `KOSDAQ` |
| name | VARCHAR(128) | Display name | `코스피`, `코스닥` |
| status | VARCHAR(16) | Status | `ACTIVE` |

**Symbols**: 2 indices (KOSPI 1001, KOSDAQ 2001).
**Sync script**: `scripts/kr_index_sync_master.py`

---

### 2.4 `us_index_master` — US Index Symbols

| Column | Type | Description | Example Values |
|--------|------|-------------|----------------|
| symbol | VARCHAR(32) PK | Index symbol | `US500`, `DJI`, `IXIC` |
| market | VARCHAR(16) | Market identifier | `SP500`, `DJI`, `IXIC` |
| name | VARCHAR(128) | Full name | `S&P 500`, `Dow Jones Industrial Average`, `NASDAQ Composite` |
| status | VARCHAR(16) | Status | `ACTIVE` |

**Symbols**: 3 indices (hardcoded).
**Sync script**: `scripts/us_index_sync_master.py`

---

### 2.5 `crypto_symbol_master` — Crypto Trading Pairs

| Column | Type | Description | Example Values |
|--------|------|-------------|----------------|
| symbol | VARCHAR(32) PK | Trading pair | `BTCUSDT`, `ETHUSDT` |
| base_asset | VARCHAR(16) | Base currency | `BTC`, `ETH`, `BNB` |
| quote_asset | VARCHAR(16) | Quote currency | `USDT` |
| status | VARCHAR(16) | Status | `ACTIVE`, `INACTIVE` |
| exchange | VARCHAR(16) | Exchange name | `BINANCE` |

**Approximate counts**: ~500+ USDT pairs on Binance.
**Sync script**: `scripts/crypto_sync_symbol_master.py`

---

## 3. Price Tables

### 3.1 Daily Price Tables (5)

| Table | Asset Class | Columns | adj_close | Volume Column | Market Column | Source | Precision |
|-------|-------------|---------|-----------|---------------|---------------|--------|-----------|
| `stock_prices` | KR Stock | OHLCV + adj_close | Yes | `volume` (BIGINT) | `market` | pykrx | DECIMAL(18,4) |
| `us_stock_prices` | US Stock | OHLCV + adj_close | Yes | `volume` (BIGINT) | `market` | fdr | DECIMAL(18,4) |
| `kr_index_prices` | KR Index | OHLCV | **No** | `volume` (BIGINT) | `market` | pykrx | DECIMAL(18,4) |
| `us_index_prices` | US Index | OHLCV | **No** | `volume` (BIGINT) | `market` | fdr | DECIMAL(18,4) |
| `crypto_prices_daily` | Crypto | OHLCV | **No** | `volume_quote` (DECIMAL) | `exchange` | binance | DECIMAL(28,10) |

**Common columns for all daily price tables**:
- `symbol` VARCHAR(32) — Primary key part 1
- `date` DATE — Primary key part 2
- `open`, `high`, `low`, `close` — OHLC prices
- `source` VARCHAR(16) — Data source identifier
- `etl_loaded_at` TIMESTAMP — Row load timestamp

**Key differences**:
- **adj_close**: Only stock tables (KR/US) have adjusted close prices. Indices and crypto do not.
- **volume_quote**: Crypto uses `volume_quote` (USDT-denominated) instead of `volume` (share count).
- **exchange vs market**: Crypto uses `exchange` (BINANCE) instead of `market` (KOSPI/NYSE).
- **Precision**: Crypto uses DECIMAL(28,10) for sub-cent precision; stocks/indices use DECIMAL(18,4).

**Market values per table**:

| Table | Market/Exchange Values |
|-------|----------------------|
| `stock_prices` | `KOSPI`, `KOSDAQ`, `KONEX` |
| `us_stock_prices` | `NYSE`, `NASDAQ`, `ETF` |
| `kr_index_prices` | `KOSPI`, `KOSDAQ` |
| `us_index_prices` | `SP500`, `DJI`, `IXIC` |
| `crypto_prices_daily` | exchange = `BINANCE` |

---

### 3.2 Weekly Price Tables (5)

| Table | Asset Class | Date Key | adj_close | Precision |
|-------|-------------|----------|-----------|-----------|
| `stock_prices_weekly` | KR Stock | `week_start` + `week_end` | Yes | DECIMAL(18,4) |
| `us_stock_prices_weekly` | US Stock | `week_start` + `week_end` | Yes | DECIMAL(18,4) |
| `kr_index_prices_weekly` | KR Index | `week_start` + `week_end` | **No** | DECIMAL(18,4) |
| `us_index_prices_weekly` | US Index | `week_start` + `week_end` | **No** | DECIMAL(18,4) |
| `crypto_prices_weekly` | Crypto | `week_start` + `week_end` | **No** | DECIMAL(28,10) |

Weekly tables use `week_start` (Monday/first trading day) as the primary key date column instead of `date`. They also include `week_end` (Friday/last trading day) as a non-key column. Weekly data is aggregated from the corresponding daily tables:
- `open` = first day's open
- `high` = max high of the week
- `low` = min low of the week
- `close` = last day's close
- `volume` / `volume_quote` = sum of the week

---

## 4. Indicator Tables

This is the core analytical content of the database. All indicator tables use a **long-form EAV** (Entity-Attribute-Value) schema. Each row stores one indicator value for one symbol on one date.

### 4.1 Indicator Table Summary

| # | Table | Asset | Timeframe | Config Key | Pipeline Indicators | IBD Indicators |
|---|-------|-------|-----------|------------|--------------------|--------------------|
| 1 | `stock_indicators` | KR Stock | Daily | `indicators` | SMA(50,100,150,200) | ibd_rs_rating, rs_line, blue_dot |
| 2 | `stock_indicators_weekly` | KR Stock | Weekly | `indicators_weekly` | SMA(20,50,100,200), EMA(21) | — |
| 3 | `kr_index_indicators` | KR Index | Daily | `indicators_kr_index` | SMA(50,100,150,200) | — |
| 4 | `kr_index_indicators_weekly` | KR Index | Weekly | `indicators_kr_index_weekly` | SMA(20,50,100,200), EMA(21) | — |
| 5 | `us_stock_indicators` | US Stock | Daily | `indicators_us` | SMA(50,100,150,200) | ibd_rs_rating, rs_line, blue_dot |
| 6 | `us_stock_indicators_weekly` | US Stock | Weekly | `indicators_us_weekly` | SMA(20,50,100,200), EMA(21) | — |
| 7 | `us_index_indicators` | US Index | Daily | `indicators_us_index` | SMA(50,100,150,200) | — |
| 8 | `us_index_indicators_weekly` | US Index | Weekly | `indicators_us_index_weekly` | SMA(20,50,100,200), EMA(21) | — |
| 9 | `crypto_indicators_daily` | Crypto | Daily | `indicators_crypto_daily` | SMA(50,100,150,200) | — |
| 10 | `crypto_indicators_weekly` | Crypto | Weekly | `indicators_crypto_weekly` | SMA(20,50,100,200) | — |

---

### 4.2 Detailed Indicator Content Per Table

#### `stock_indicators` (KR Stock Daily)

| Indicator | indicator column value | Parameters | Description | Value Range |
|-----------|-----------------------|------------|-------------|-------------|
| SMA 50-day | `sma_50_close` | `{window: 50, column: close}` | 50-day simple moving average of close | Same as price |
| SMA 100-day | `sma_100_close` | `{window: 100, column: close}` | 100-day simple moving average of close | Same as price |
| SMA 150-day | `sma_150_close` | `{window: 150, column: close}` | 150-day simple moving average of close | Same as price |
| SMA 200-day | `sma_200_close` | `{window: 200, column: close}` | 200-day simple moving average of close | Same as price |
| IBD RS Rating | `ibd_rs_rating` | `{strict_12m: true}` | Cross-sectional relative strength percentile | 1 ~ 99 |
| RS Line | `rs_line` | `{benchmark: "1001"}` | Stock close / KOSPI index close ratio | > 0 (ratio) |
| Blue Dot | `blue_dot` | `{lookback: 252, benchmark: "1001"}` | RS Line at 52-week high while price is NOT at 52-week high | 0 or 1 |

#### `stock_indicators_weekly` (KR Stock Weekly)

| Indicator | indicator column value | Parameters | Description |
|-----------|-----------------------|------------|-------------|
| SMA 20-week | `sma_20_close` | `{window: 20, column: close}` | 20-week simple moving average |
| SMA 50-week | `sma_50_close` | `{window: 50, column: close}` | 50-week simple moving average |
| SMA 100-week | `sma_100_close` | `{window: 100, column: close}` | 100-week simple moving average |
| SMA 200-week | `sma_200_close` | `{window: 200, column: close}` | 200-week simple moving average |
| EMA 21-week | `ema_21_close` | `{window: 21, column: close}` | 21-week exponential moving average |

#### `kr_index_indicators` (KR Index Daily)

| Indicator | indicator column value | Parameters | Description |
|-----------|-----------------------|------------|-------------|
| SMA 50-day | `sma_50_close` | `{window: 50, column: close}` | 50-day SMA |
| SMA 100-day | `sma_100_close` | `{window: 100, column: close}` | 100-day SMA |
| SMA 150-day | `sma_150_close` | `{window: 150, column: close}` | 150-day SMA |
| SMA 200-day | `sma_200_close` | `{window: 200, column: close}` | 200-day SMA |

#### `kr_index_indicators_weekly` (KR Index Weekly)

| Indicator | indicator column value | Parameters | Description |
|-----------|-----------------------|------------|-------------|
| SMA 20-week | `sma_20_close` | `{window: 20, column: close}` | 20-week SMA |
| SMA 50-week | `sma_50_close` | `{window: 50, column: close}` | 50-week SMA |
| SMA 100-week | `sma_100_close` | `{window: 100, column: close}` | 100-week SMA |
| SMA 200-week | `sma_200_close` | `{window: 200, column: close}` | 200-week SMA |
| EMA 21-week | `ema_21_close` | `{window: 21, column: close}` | 21-week EMA |

#### `us_stock_indicators` (US Stock Daily)

| Indicator | indicator column value | Parameters | Description | Value Range |
|-----------|-----------------------|------------|-------------|-------------|
| SMA 50-day | `sma_50_close` | `{window: 50, column: close}` | 50-day SMA | Same as price |
| SMA 100-day | `sma_100_close` | `{window: 100, column: close}` | 100-day SMA | Same as price |
| SMA 150-day | `sma_150_close` | `{window: 150, column: close}` | 150-day SMA | Same as price |
| SMA 200-day | `sma_200_close` | `{window: 200, column: close}` | 200-day SMA | Same as price |
| IBD RS Rating | `ibd_rs_rating` | `{strict_12m: true}` | Cross-sectional relative strength percentile | 1 ~ 99 |
| RS Line | `rs_line` | `{benchmark: "US500"}` | Stock close / S&P 500 index close ratio | > 0 (ratio) |
| Blue Dot | `blue_dot` | `{lookback: 252, benchmark: "US500"}` | RS Line at 52-week high, price NOT at 52-week high | 0 or 1 |

#### `us_stock_indicators_weekly` (US Stock Weekly)

| Indicator | indicator column value | Parameters | Description |
|-----------|-----------------------|------------|-------------|
| SMA 20-week | `sma_20_close` | `{window: 20, column: close}` | 20-week SMA |
| SMA 50-week | `sma_50_close` | `{window: 50, column: close}` | 50-week SMA |
| SMA 100-week | `sma_100_close` | `{window: 100, column: close}` | 100-week SMA |
| SMA 200-week | `sma_200_close` | `{window: 200, column: close}` | 200-week SMA |
| EMA 21-week | `ema_21_close` | `{window: 21, column: close}` | 21-week EMA |

#### `us_index_indicators` (US Index Daily)

| Indicator | indicator column value | Parameters | Description |
|-----------|-----------------------|------------|-------------|
| SMA 50-day | `sma_50_close` | `{window: 50, column: close}` | 50-day SMA |
| SMA 100-day | `sma_100_close` | `{window: 100, column: close}` | 100-day SMA |
| SMA 150-day | `sma_150_close` | `{window: 150, column: close}` | 150-day SMA |
| SMA 200-day | `sma_200_close` | `{window: 200, column: close}` | 200-day SMA |

#### `us_index_indicators_weekly` (US Index Weekly)

| Indicator | indicator column value | Parameters | Description |
|-----------|-----------------------|------------|-------------|
| SMA 20-week | `sma_20_close` | `{window: 20, column: close}` | 20-week SMA |
| SMA 50-week | `sma_50_close` | `{window: 50, column: close}` | 50-week SMA |
| SMA 100-week | `sma_100_close` | `{window: 100, column: close}` | 100-week SMA |
| SMA 200-week | `sma_200_close` | `{window: 200, column: close}` | 200-week SMA |
| EMA 21-week | `ema_21_close` | `{window: 21, column: close}` | 21-week EMA |

#### `crypto_indicators_daily` (Crypto Daily)

| Indicator | indicator column value | Parameters | Description |
|-----------|-----------------------|------------|-------------|
| SMA 50-day | `sma_50_close` | `{window: 50, column: close}` | 50-day SMA |
| SMA 100-day | `sma_100_close` | `{window: 100, column: close}` | 100-day SMA |
| SMA 150-day | `sma_150_close` | `{window: 150, column: close}` | 150-day SMA |
| SMA 200-day | `sma_200_close` | `{window: 200, column: close}` | 200-day SMA |

#### `crypto_indicators_weekly` (Crypto Weekly)

| Indicator | indicator column value | Parameters | Description |
|-----------|-----------------------|------------|-------------|
| SMA 20-week | `sma_20_close` | `{window: 20, column: close}` | 20-week SMA |
| SMA 50-week | `sma_50_close` | `{window: 50, column: close}` | 50-week SMA |
| SMA 100-week | `sma_100_close` | `{window: 100, column: close}` | 100-week SMA |
| SMA 200-week | `sma_200_close` | `{window: 200, column: close}` | 200-week SMA |

---

### 4.3 IBD Indicators (Cross-Sectional)

IBD (Investor's Business Daily) indicators are **cross-sectional** — they require data from ALL symbols to compute percentile rankings. They are only available for **stock** daily tables (KR and US), not for indices, crypto, or weekly tables.

#### IBD RS Rating (`ibd_rs_rating`)

- **What**: Relative strength rating from 1 (worst) to 99 (best) based on weighted multi-period returns
- **Weights**: 40% x 3-month + 20% x 6-month + 20% x 9-month + 20% x 12-month return
- **strict_12m**: When `true`, excludes stocks with less than 12 months of price history
- **Tables**: `stock_indicators` (benchmark: KOSPI), `us_stock_indicators` (benchmark: S&P 500)
- **Update scripts**: `scripts/kr_rs_update.py`, `scripts/us_rs_update.py`

#### RS Line (`rs_line`)

- **What**: Stock price relative to benchmark index (stock_close / index_close)
- **Benchmarks**: KOSPI index `1001` for KR stocks, S&P 500 `US500` for US stocks
- **Interpretation**: Rising RS Line = stock outperforming benchmark
- **Tables**: `stock_indicators`, `us_stock_indicators`

#### Blue Dot (`blue_dot`)

- **What**: Binary signal (0 or 1). Fires when RS Line makes a new 52-week high while the stock price itself is NOT at a 52-week high
- **Lookback**: 252 trading days (1 year)
- **Interpretation**: Leading strength indicator — relative strength breaking out before price does
- **Tables**: `stock_indicators`, `us_stock_indicators`

---

## 5. Screening & Utility Tables

### 5.1 `minervini_screen_results_kr` — Minervini Trend Template Screening (KR Stock)

Mark Minervini의 트렌드 템플릿 8가지 조건을 사전 배치로 계산하여 저장. 통과한 종목만 저장 (탈락 종목 제외).

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| symbol | VARCHAR(32) PK | 종목 코드 | `005930` |
| date | DATE PK | 스크리닝 날짜 | `2026-02-07` |
| market | VARCHAR(16) | 시장 구분 | `KOSPI`, `KOSDAQ`, `ETF` |
| rs_rating | DECIMAL(5,1) | IBD RS Rating (1~99) | `85.2` |
| is_blue_dot | TINYINT | Blue Dot 신호 (0/1) | `1` |
| screen_config_hash | CHAR(40) PK | 스크리닝 설정 해시 | `abc123...` |
| failed_reason | VARCHAR(512) | 탈락 사유 (미사용) | NULL |
| created_at | TIMESTAMP | 레코드 생성 시각 | `2026-02-07 17:00:00` |

**Primary Key**: `(symbol, date, screen_config_hash)`
**Storage**: 통과 종목만 저장 (INSERT ONLY)
**Config**: `minervini_kr` in `config/settings.yaml`
**Script**: `scripts/kr_minervini_update.py --days 7 --force`

**스크리닝 조건**:
- MA 정배열 (price > sma50 > sma150 > sma200)
- SMA200 상승 추세 (22거래일 전보다 높음)
- 52주 저가 대비 130% 이상
- 52주 고가의 75% 이상
- RS Rating 80 이상
- Blue Dot (선택적, 기본값 False)

---

### 5.2 `minervini_screen_results_us` — Minervini Trend Template Screening (US Stock)

동일한 구조 (market: NYSE/NASDAQ/ETF).

**Config**: `minervini_us` in `config/settings.yaml`
**Script**: `scripts/us_minervini_update.py --days 7 --force`

---

### 5.3 `watchlist_items` — User Watchlist Utility Table

Grafana 사용자별 관심 종목/상태(BUY_ALERT, HIGH_ON_DECK, WATCHLIST, DISCARD)를 저장하는 보조 테이블.

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| id | BIGINT UNSIGNED PK AI | 레코드 ID | `1` |
| user_id | BIGINT UNSIGNED | Grafana user id | `12` |
| user_login | VARCHAR(190) | 사용자 로그인명 | `hank` |
| market | VARCHAR(8) | 마켓 구분 | `KR`, `US` |
| symbol | VARCHAR(32) | 종목 코드 | `005930`, `AAPL` |
| group_type | ENUM | 관심 그룹 | `BUY_ALERT`, `WATCHLIST` |
| note | TEXT | 사용자 메모 | `관찰 필요` |
| created_at | DATETIME | 생성 시각 | `2026-02-20 09:00:00` |
| updated_at | DATETIME | 수정 시각 | `2026-02-26 08:10:00` |

**Primary Key**: `(id)`
**Unique Key**: `(user_id, market, symbol)`

---

## 6. Database Views

Views join price tables with indicator tables, pivoting the long-form indicator rows into wide-form columns for easy querying.

### 6.1 View Summary

| View | Source Tables | Available Columns |
|------|-------------|-------------------|
| `v_stock_price_with_ma` | `stock_prices` + `stock_indicators` | symbol, date, OHLCV, **sma_50, sma_100, sma_150, sma_200, rs_line** |
| `v_stock_price_weekly_with_ma` | `stock_prices_weekly` + `stock_indicators_weekly` | symbol, week_start, week_end, OHLCV, **sma_20, sma_50, sma_100, sma_200, ema_21** |
| `v_kr_index_price_with_ma` | `kr_index_prices` + `kr_index_indicators` | symbol, date, OHLCV, **sma_50, sma_100, sma_150, sma_200** |
| `v_kr_index_price_weekly_with_ma` | `kr_index_prices_weekly` + `kr_index_indicators_weekly` | symbol, week_start, week_end, OHLCV, **sma_5, sma_20, ema_12, ema_26** |
| `v_us_stock_price_with_ma` | `us_stock_prices` + `us_stock_indicators` | symbol, date, OHLCV, **sma_50, sma_100, sma_150, sma_200, rs_line** |
| `v_us_stock_price_weekly_with_ma` | `us_stock_prices_weekly` + `us_stock_indicators_weekly` | symbol, week_start, week_end, OHLCV, **sma_20, sma_50, sma_100, sma_200, ema_21** |
| `v_us_index_price_with_ma` | `us_index_prices` + `us_index_indicators` | symbol, date, OHLCV, **sma_50, sma_100, sma_150, sma_200** |
| `v_us_index_price_weekly_with_ma` | `us_index_prices_weekly` + `us_index_indicators_weekly` | symbol, week_start, week_end, OHLCV, **sma_5, sma_20, sma_40** |
| `v_crypto_price_weekly_with_ma` | `crypto_prices_weekly` + `crypto_indicators_weekly` | symbol, week_start, week_end, OHLCV, **sma_20, sma_50, sma_100, sma_200, ema_21** |
| `v_watchlist_items_kr` | `watchlist_items` + `symbol_master` | watchlist columns + **name, kr_market, sector, industry** |

### 6.2 View Details

**Note**: Views include pipeline indicators (SMA) and selected cross-sectional indicators (RS Line for stock views). IBD RS Rating, Blue Dot, and Minervini screening results must be queried directly from indicator/screening tables.

**주의 (실제 적재 데이터 기준)**:
- `v_kr_index_price_weekly_with_ma`의 `sma_5`, `ema_12`, `ema_26`는 현재 파이프라인/적재 패턴과 달라 대부분 NULL일 수 있음.
- `v_us_index_price_weekly_with_ma`의 `sma_5`, `sma_40`도 동일 이유로 대부분 NULL일 수 있음.
- `v_crypto_price_weekly_with_ma`의 `ema_21`은 현재 적재 테이블 기준으로 NULL일 수 있음.

#### `v_stock_price_with_ma` — KR Stock Daily + Moving Averages

```
Columns: symbol, date, open, high, low, close, volume, sma_50, sma_100, sma_150, sma_200, rs_line
```

#### `v_stock_price_weekly_with_ma` — KR Stock Weekly

```
Columns: symbol, week_start, week_end, open, high, low, close, volume, sma_20, sma_50, sma_100, sma_200, ema_21
```

#### `v_kr_index_price_with_ma` — KR Index Daily

```
Columns: symbol, date, open, high, low, close, volume, sma_50, sma_100, sma_150, sma_200
```

#### `v_kr_index_price_weekly_with_ma` — KR Index Weekly

```
Columns: symbol, week_start, week_end, open, high, low, close, volume, sma_5, sma_20, ema_12, ema_26
```

#### `v_us_stock_price_with_ma` — US Stock Daily + Moving Averages

```
Columns: symbol, date, open, high, low, close, volume, sma_50, sma_100, sma_150, sma_200, rs_line
```

#### `v_us_stock_price_weekly_with_ma` — US Stock Weekly

```
Columns: symbol, week_start, week_end, open, high, low, close, volume, sma_20, sma_50, sma_100, sma_200, ema_21
```

#### `v_us_index_price_with_ma` — US Index Daily

```
Columns: symbol, date, open, high, low, close, volume, sma_50, sma_100, sma_150, sma_200
```

#### `v_us_index_price_weekly_with_ma` — US Index Weekly

```
Columns: symbol, week_start, week_end, open, high, low, close, volume, sma_5, sma_20, sma_40
```

#### `v_crypto_price_weekly_with_ma` — Crypto Weekly

```
Columns: symbol, week_start, week_end, open, high, low, close, volume_quote, sma_20, sma_50, sma_100, sma_200, ema_21
```

#### `v_watchlist_items_kr` — KR Watchlist + Symbol Metadata

```
Columns: id, user_id, user_login, market, symbol, group_type, note, created_at, updated_at, name, kr_market, sector, industry
```

---

## 7. Indicator Storage Pattern

### 6.1 Long-Form EAV Schema

All indicator tables use a long-form EAV (Entity-Attribute-Value) schema:

```
PRIMARY KEY (symbol, date/week_start, indicator, params_hash)
```

Each row stores exactly ONE indicator value:

| symbol | date | indicator | params_hash | value |
|--------|------|-----------|-------------|-------|
| 005930 | 2024-12-31 | sma_50_close | a1b2c3d4... | 57820.0000 |
| 005930 | 2024-12-31 | sma_200_close | e5f6g7h8... | 58100.0000 |
| 005930 | 2024-12-31 | ibd_rs_rating | i9j0k1l2... | 85.0000 |

### 6.2 params_hash Concept

The `params_hash` is a SHA-1 hash of the indicator name + its parameters. This allows multiple parameter variants of the same indicator to coexist:

```
sma(window=5, column=close)   -> params_hash = SHA1("sma" + '{"column":"close","window":5}')
sma(window=20, column=close)  -> params_hash = SHA1("sma" + '{"column":"close","window":20}')
```

The hash is deterministic: same indicator + same params always produces the same hash.

### 6.3 Indicator Naming Convention

The `indicator` column follows the pattern: `{name}_{window}_{column}`

| Type | indicator value | Example |
|------|----------------|---------|
| SMA | `sma_{window}_close` | `sma_5_close`, `sma_200_close` |
| EMA | `ema_{window}_close` | `ema_12_close`, `ema_21_close` |
| IBD RS Rating | `ibd_rs_rating` | `ibd_rs_rating` |
| RS Line | `rs_line` | `rs_line` |
| Blue Dot | `blue_dot` | `blue_dot` |

---

## 8. Key Differences Between Asset Classes

### 7.1 Column Differences

| Feature | KR/US Stock | KR/US Index | Crypto |
|---------|-------------|-------------|--------|
| adj_close | Yes | No | No |
| Volume column | `volume` (BIGINT) | `volume` (BIGINT) | `volume_quote` (DECIMAL) |
| Market/Exchange col | `market` | `market` | `exchange` |
| Price precision | DECIMAL(18,4) | DECIMAL(18,4) | DECIMAL(28,10) |
| Indicator precision | DECIMAL(28,10) | DECIMAL(28,10) | DECIMAL(28,10) |

### 7.2 Feature Availability

| Feature | KR Stock | US Stock | KR Index | US Index | Crypto |
|---------|----------|----------|----------|----------|--------|
| Daily prices | Yes | Yes | Yes | Yes | Yes |
| Weekly prices | Yes | Yes | Yes | Yes | Yes |
| Daily SMA/EMA | Yes | Yes | Yes | Yes | Yes |
| Weekly SMA/EMA | Yes | Yes | Yes | Yes | Yes |
| IBD RS Rating | Yes | Yes | No | No | No |
| RS Line | Yes | Yes | No | No | No |
| Blue Dot | Yes | Yes | No | No | No |
| Sector/Industry | Yes | Yes | No | No | No |
| Daily View | Yes | Yes | Yes | Yes | — |
| Weekly View | Yes | Yes | Yes | Yes | Yes |

### 7.3 Data Source Summary

| Data Source | Asset Classes | Rate Limit |
|-------------|--------------|------------|
| pykrx | KR Stock, KR Index | ~5 req/sec (configurable) |
| FinanceDataReader (FDR) | US Stock, US Index, KR Stock (legacy) | ~5 req/sec (configurable) |
| Binance API | Crypto | Standard Binance limits |

---

## 9. Sample Queries for Grafana

### 9.1 Using Views (Simplest)

```sql
-- KR Stock: Samsung Electronics daily chart with moving averages
SELECT date, close, sma_50, sma_100, sma_150, sma_200, rs_line
FROM v_stock_price_with_ma
WHERE symbol = '005930'
  AND date >= '2024-01-01'
ORDER BY date;

-- US Stock: Apple daily chart with moving averages
SELECT date, close, sma_50, sma_100, sma_150, sma_200, rs_line
FROM v_us_stock_price_with_ma
WHERE symbol = 'AAPL'
  AND date >= '2024-01-01'
ORDER BY date;

-- US Index: S&P 500 daily with moving averages
SELECT date, close, sma_50, sma_100, sma_150, sma_200
FROM v_us_index_price_with_ma
WHERE symbol = 'US500'
  AND date >= '2024-01-01'
ORDER BY date;

-- Crypto: BTC weekly with long-term MAs
SELECT week_start, close, sma_20, sma_50, sma_100, sma_200, ema_21
FROM v_crypto_price_weekly_with_ma
WHERE symbol = 'BTCUSDT'
ORDER BY week_start;
```

### 9.2 Querying Indicator Tables Directly

```sql
-- Get IBD RS Rating for a specific stock
SELECT date, value AS rs_rating
FROM us_stock_indicators
WHERE symbol = 'AAPL'
  AND indicator = 'ibd_rs_rating'
  AND date >= '2024-01-01'
ORDER BY date;

-- Get RS Line for Samsung Electronics
SELECT date, value AS rs_line
FROM stock_indicators
WHERE symbol = '005930'
  AND indicator = 'rs_line'
  AND date >= '2024-01-01'
ORDER BY date;

-- Get Blue Dot signals for all US stocks on a specific date
SELECT si.symbol, sm.name, si.value AS blue_dot
FROM us_stock_indicators si
JOIN us_symbol_master sm ON si.symbol = sm.symbol
WHERE si.indicator = 'blue_dot'
  AND si.date = '2024-12-31'
  AND si.value = 1
ORDER BY si.symbol;
```

### 9.3 Joining Price + Indicator Tables Manually

```sql
-- US Stock daily price with all indicators (including IBD)
SELECT
  p.symbol, p.date, p.close, p.volume,
  MAX(CASE WHEN i.indicator = 'sma_50_close'   THEN i.value END) AS sma_50,
  MAX(CASE WHEN i.indicator = 'sma_100_close'  THEN i.value END) AS sma_100,
  MAX(CASE WHEN i.indicator = 'sma_150_close'  THEN i.value END) AS sma_150,
  MAX(CASE WHEN i.indicator = 'sma_200_close'  THEN i.value END) AS sma_200,
  MAX(CASE WHEN i.indicator = 'ibd_rs_rating'  THEN i.value END) AS rs_rating,
  MAX(CASE WHEN i.indicator = 'rs_line'        THEN i.value END) AS rs_line,
  MAX(CASE WHEN i.indicator = 'blue_dot'       THEN i.value END) AS blue_dot
FROM us_stock_prices p
LEFT JOIN us_stock_indicators i
  ON p.symbol = i.symbol AND p.date = i.date
WHERE p.symbol = 'AAPL'
  AND p.date >= '2024-01-01'
GROUP BY p.symbol, p.date, p.close, p.volume
ORDER BY p.date;
```

### 9.4 Cross-Market Comparison

```sql
-- Compare KR index vs US index (daily close, normalized)
SELECT
  ki.date,
  ki.close AS kospi_close,
  ui.close AS sp500_close
FROM kr_index_prices ki
JOIN us_index_prices ui ON ki.date = ui.date
WHERE ki.symbol = '1001'      -- KOSPI
  AND ui.symbol = 'US500'     -- S&P 500
  AND ki.date >= '2024-01-01'
ORDER BY ki.date;
```

### 9.5 RS Rating Distribution (Histogram)

```sql
-- Distribution of RS Ratings for US stocks on the latest date
SELECT
  FLOOR(value / 10) * 10 AS rs_bucket,
  COUNT(*) AS count
FROM us_stock_indicators
WHERE indicator = 'ibd_rs_rating'
  AND date = (SELECT MAX(date) FROM us_stock_indicators WHERE indicator = 'ibd_rs_rating')
GROUP BY rs_bucket
ORDER BY rs_bucket;
```

### 9.6 Top RS Rating Stocks

```sql
-- Top 20 US stocks by RS Rating (latest date)
SELECT si.symbol, sm.name, sm.market, sm.sector, si.value AS rs_rating
FROM us_stock_indicators si
JOIN us_symbol_master sm ON si.symbol = sm.symbol
WHERE si.indicator = 'ibd_rs_rating'
  AND si.date = (SELECT MAX(date) FROM us_stock_indicators WHERE indicator = 'ibd_rs_rating')
ORDER BY si.value DESC
LIMIT 20;
```

### 9.7 Active Symbol Count by Market

```sql
-- KR stocks
SELECT market, COUNT(*) AS count FROM symbol_master WHERE status = 'ACTIVE' GROUP BY market;

-- US stocks
SELECT market, COUNT(*) AS count FROM us_symbol_master WHERE status = 'ACTIVE' GROUP BY market;

-- Crypto
SELECT exchange, COUNT(*) AS count FROM crypto_symbol_master WHERE status = 'ACTIVE' GROUP BY exchange;
```

### 9.8 Minervini Trend Template Screening

```sql
-- Get all KR stocks passing Minervini screening on the latest date
SELECT
  m.symbol,
  sm.name,
  m.market,
  sm.sector,
  m.rs_rating,
  m.is_blue_dot
FROM minervini_screen_results_kr m
JOIN symbol_master sm ON m.symbol = sm.symbol
WHERE m.date = (SELECT MAX(date) FROM minervini_screen_results_kr)
ORDER BY m.rs_rating DESC
LIMIT 50;

-- Get US stocks with Blue Dot passing Minervini screening
SELECT
  m.symbol,
  sm.name,
  m.market,
  m.rs_rating,
  m.is_blue_dot
FROM minervini_screen_results_us m
JOIN us_symbol_master sm ON m.symbol = sm.symbol
WHERE m.date = (SELECT MAX(date) FROM minervini_screen_results_us)
  AND m.is_blue_dot = 1
ORDER BY m.rs_rating DESC;

-- Daily trend: count of stocks passing Minervini screening (last 30 days)
SELECT
  date,
  market,
  COUNT(*) as pass_count
FROM minervini_screen_results_kr
WHERE date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
GROUP BY date, market
ORDER BY date DESC, market;
```

### 9.9 Data Freshness Check

```sql
-- Latest data date per asset class
SELECT 'KR Stock' AS asset, MAX(date) AS latest FROM stock_prices
UNION ALL
SELECT 'US Stock', MAX(date) FROM us_stock_prices
UNION ALL
SELECT 'KR Index', MAX(date) FROM kr_index_prices
UNION ALL
SELECT 'US Index', MAX(date) FROM us_index_prices
UNION ALL
SELECT 'Crypto', MAX(date) FROM crypto_prices_daily
UNION ALL
SELECT 'Minervini KR', MAX(date) FROM minervini_screen_results_kr
UNION ALL
SELECT 'Minervini US', MAX(date) FROM minervini_screen_results_us;
```
