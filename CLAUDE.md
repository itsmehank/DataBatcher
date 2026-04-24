# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DataBatcher is a multi-market stock data collection and technical indicator calculation system. It supports Korean (KRX), US (NYSE/NASDAQ), and Crypto (Binance) markets. It fetches price data from various sources (pykrx, FinanceDataReader, Binance API), computes technical indicators (SMA, EMA, etc.), and stores everything in MySQL for analysis and trading strategy backtesting.

**Supported Markets**:
- **Korean (KRX)**: KOSPI, KOSDAQ, KONEX, ETF via pykrx
- **US**: NYSE, NASDAQ, US ETF via FinanceDataReader
- **Crypto**: Binance Spot (USDT pairs) via Binance API

**Core Pipeline**: Data Collection (collectors) → Indicator Calculation (indicators) → Database Storage (savers)

**Monorepo**: `apps/ingest-databatcher/` is the main app. Other apps (`apps/trading-view-project/`, `apps/my-insight-archieve/`, `apps/real-estate-project/`) are independently deployed.

## Development Commands

### Environment Setup
```bash
pip install -r requirements.txt
docker compose -f db/compose/mysql-standalone/docker-compose-mysql.yaml up -d
python apps/ingest-databatcher/scripts/init_db.py

# DB connection check
python apps/ingest-databatcher/scripts/healthcheck_db.py

# Preflight safety check (repo path sanity)
python apps/ingest-databatcher/scripts/preflight_repo_safety.py
```

MySQL is running as `grafana-with-db-mysql` (check `docker ps`). Credentials are in `.env`.

### Quick Start (First Run)
```bash
# 1. Sync symbol masters
python apps/ingest-databatcher/scripts/sync_symbol_master.py    # KR stocks
python apps/ingest-databatcher/scripts/us_sync_symbol_master.py # US stocks (--skip-yfinance for speed)
python apps/ingest-databatcher/scripts/us_index_sync_master.py  # US indices
python apps/ingest-databatcher/scripts/kr_index_sync_master.py  # KR indices
python apps/ingest-databatcher/scripts/crypto_sync_symbol_master.py

# 2. Bulk historical load (test with --top 100 first)
python apps/ingest-databatcher/scripts/bulk_update.py --start 2024-01-01 --end 2024-12-31 --top 100 --workers 4

# 3. Daily update test
python apps/ingest-databatcher/scripts/daily_update.py --all --top 10 --force
```

### KR Stock Commands
```bash
# Symbol master (weekly)
python apps/ingest-databatcher/scripts/sync_symbol_master.py

# Bulk collection (initial/backfill)
python apps/ingest-databatcher/scripts/bulk_update.py --start 2020-01-01 --end 2024-12-31 --workers 8
python apps/ingest-databatcher/scripts/bulk_update.py --start 2024-01-01 --end 2024-12-31 --market KOSPI --workers 4
python apps/ingest-databatcher/scripts/bulk_update_weekly.py

# Daily / weekly incremental
python apps/ingest-databatcher/scripts/daily_update.py --all --force
python apps/ingest-databatcher/scripts/daily_update.py --all --market KOSPI --force
python apps/ingest-databatcher/scripts/weekly_update.py --all

# RS indicators (after daily_update)
python apps/ingest-databatcher/scripts/kr_rs_update.py --force
python apps/ingest-databatcher/scripts/kr_rs_update.py --market KOSPI --days 5 --force

# Minervini screening (after rs_update)
python apps/ingest-databatcher/scripts/kr_minervini_update.py --days 7 --force
python apps/ingest-databatcher/scripts/kr_minervini_update.py --days 9999 --force  # full backfill
```

### KR Index Commands
```bash
python apps/ingest-databatcher/scripts/kr_index_sync_master.py
python apps/ingest-databatcher/scripts/kr_index_bulk_update.py --start 2020-01-01 --end 2024-12-31
python apps/ingest-databatcher/scripts/kr_index_daily_update.py --all --force
python apps/ingest-databatcher/scripts/kr_index_bulk_update_weekly.py
python apps/ingest-databatcher/scripts/kr_index_weekly_update.py --all
```

### US Stock Commands
```bash
# Symbol master (weekly; --skip-yfinance for faster run)
python apps/ingest-databatcher/scripts/us_sync_symbol_master.py
python apps/ingest-databatcher/scripts/us_sync_symbol_master.py --market NASDAQ --skip-yfinance

# Bulk / daily / weekly
python apps/ingest-databatcher/scripts/us_bulk_update.py --start 2024-01-01 --end 2024-12-31 --workers 4 --with-indicators
python apps/ingest-databatcher/scripts/us_bulk_update_weekly.py
python apps/ingest-databatcher/scripts/us_daily_update.py --all --with-indicators
python apps/ingest-databatcher/scripts/us_weekly_update.py --all

# RS indicators and Minervini
python apps/ingest-databatcher/scripts/us_rs_update.py --force
python apps/ingest-databatcher/scripts/us_minervini_update.py --days 7 --force
```

### US Index Commands
```bash
python apps/ingest-databatcher/scripts/us_index_sync_master.py
python apps/ingest-databatcher/scripts/us_index_bulk_update.py --start 2020-01-01 --end 2024-12-31
python apps/ingest-databatcher/scripts/us_index_daily_update.py --all --force
python apps/ingest-databatcher/scripts/us_index_bulk_update_weekly.py
python apps/ingest-databatcher/scripts/us_index_weekly_update.py --all
```

### Crypto Commands
```bash
python apps/ingest-databatcher/scripts/crypto_sync_symbol_master.py
python apps/ingest-databatcher/scripts/crypto_bulk_update_daily.py --all --with-indicators
python apps/ingest-databatcher/scripts/crypto_bulk_update_weekly.py --all
python apps/ingest-databatcher/scripts/crypto_daily_update.py --all --with-indicators
python apps/ingest-databatcher/scripts/crypto_weekly_update.py --all
```

### Indicator Backfill (Independent from Data Collection)
```bash
# Recalculate indicators from existing DB price data (no API calls)
python apps/ingest-databatcher/scripts/backfill_indicators.py --source stock_prices
python apps/ingest-databatcher/scripts/backfill_indicators.py --source us_stock_prices --market NASDAQ --workers 8
python apps/ingest-databatcher/scripts/backfill_indicators.py --source stock_prices --mode upsert  # overwrite
```

### Shell Orchestration Scripts (`apps/ingest-databatcher/ops/shell/`)
```bash
bash apps/ingest-databatcher/ops/shell/daily_all.sh        # All markets daily (~30-60 min)
bash apps/ingest-databatcher/ops/shell/daily_kr.sh
bash apps/ingest-databatcher/ops/shell/daily_us.sh
bash apps/ingest-databatcher/ops/shell/daily_crypto.sh
bash apps/ingest-databatcher/ops/shell/weekly_all.sh
bash apps/ingest-databatcher/ops/shell/bulk_all.sh         # Full bulk collection (~2-3 hours)
bash apps/ingest-databatcher/ops/shell/bulk_all_test.sh    # Bulk collection test run
bash apps/ingest-databatcher/ops/shell/bulk_all_except_symbols.sh
bash apps/ingest-databatcher/ops/shell/refresh_kr_sector_snapshot.sh
bash apps/ingest-databatcher/ops/shell/db_backup_monthly.sh
bash apps/ingest-databatcher/ops/shell/db_restore_full.sh
bash apps/ingest-databatcher/ops/shell/truncate_all_tables.sh
bash apps/ingest-databatcher/ops/shell/truncate_all_tables_custom.sh
```

### DB Table Management
```bash
# Drop / truncate / delete rows from any table
python apps/ingest-databatcher/scripts/table_manipulate/manage_table.py drop --table stock_prices
python apps/ingest-databatcher/scripts/table_manipulate/manage_table.py truncate --table stock_indicators
python apps/ingest-databatcher/scripts/table_manipulate/manage_table.py delete-symbol --table stock_prices --symbol 005930
python apps/ingest-databatcher/scripts/table_manipulate/manage_table.py delete-rows --table stock_indicators --symbol 005930 --column indicator --value sma_5_close

# Test DB (trade_test)
python apps/ingest-databatcher/scripts/init_test_db.py
```

### Probes and Tests
```bash
# Data source probes (live API checks)
python apps/ingest-databatcher/scripts/probes/fdr_stock_probe.py --symbol 005930 --start 2020-01-01 --end 2020-12-31
python apps/ingest-databatcher/scripts/probes/fdr_us_stock_probe.py --symbol AAPL --start 2024-01-01 --end 2024-01-31
python apps/ingest-databatcher/scripts/probes/fdr_us_index_probe.py
python apps/ingest-databatcher/scripts/probes/pykrx_index_probe.py
python apps/ingest-databatcher/scripts/probes/yfinance_us_stock_probe.py   # yfinance column/format check
python apps/ingest-databatcher/scripts/probes/yfinance_us_index_probe.py   # yfinance index ticker mapping check

# KR delist / symbol verification
python apps/ingest-databatcher/scripts/kr_delist_probe.py          # pykrx-based delist detection
python apps/ingest-databatcher/scripts/verify_krx_symbols.py       # verify symbols exist in FDR KRX listing

# US FDR freshness monitor
python apps/ingest-databatcher/scripts/monitor_us_fdr_freshness.py  # check FDR data lag vs market calendar

# Integration / unit tests (in scripts/tests/)
python apps/ingest-databatcher/scripts/tests/test_weekly_aggregation_unit.py
python apps/ingest-databatcher/scripts/tests/test_crypto_weekly_update_idempotency.py
python apps/ingest-databatcher/scripts/tests/test_us_weekly_update_idempotency.py
# DB assertion scripts (verify table state)
python apps/ingest-databatcher/scripts/tests/db_crypto_assert_counts.py
python apps/ingest-databatcher/scripts/tests/db_us_assert_weekly_counts.py

# Phase-based integration test suite (apps/ingest-databatcher/tests/)
python apps/ingest-databatcher/tests/run_all_tests.py               # runs Phase 1-3 sequentially
python apps/ingest-databatcher/tests/test_phase1_sync_symbol_master.py
python apps/ingest-databatcher/tests/test_phase2_bulk_update.py
python apps/ingest-databatcher/tests/test_phase3_daily_update_all.py
python apps/ingest-databatcher/tests/test_phase4_weekly_update.py
```

## High-Level Architecture

### Configuration System (`core/config_loader.py`)
Settings precedence (highest first):
1. Environment variable `DATABASE_URL` (overrides `database.url`)
2. `config/settings.dev.yaml` (development overlay)
3. `config/settings.yaml` (base)

Merged hierarchically via `merge_dict()`. All scripts call `load_settings()`.

### Database Layer (`core/db_manager.py`)
- **DBManager**: Singleton-style SQLAlchemy engine manager
  - `get_engine()`: Shared engine (created on first call)
  - `get_latest_date(symbol, table)`: Most recent date for incremental updates
  - `upsert_dataframe(df, table, mode)`: Bulk write via `ON DUPLICATE KEY UPDATE`
- **Upsert modes**:
  - `mode="insert_only"`: Preserves existing rows; used by all bulk scripts (idempotent re-runs)
  - `mode="upsert"`: Overwrites existing rows; used for indicator recalculations
- Connection pool via `DBConfig` dataclass (pool_size, max_overflow, pool_recycle, pool_pre_ping)
- All tables use `utf8mb4`. `DATABASE_URL` must include `?charset=utf8mb4`

### Collectors (`collectors/`)
All extend `BaseCollector` (`core/base_collector.py`).

| Collector | Source | Table | Notes |
|---|---|---|---|
| `KRStockCollector` (kr_stock.py) | pykrx | `stock_prices` | has `adj_close` |
| `KRIndexCollector` (kr_index.py) | pykrx | `kr_index_prices` | no `adj_close` |
| `KRETFCollector` (kr_etf.py) | pykrx | `stock_prices` | ETF-specific logic |
| `USStockCollector` (us_stock.py) | FinanceDataReader | `us_stock_prices` | has `adj_close` |
| `USIndexCollector` (us_index.py) | FinanceDataReader | `us_index_prices` | no `adj_close` |
| `BinanceCryptoCollector` (crypto_binance.py) | Binance API | `crypto_prices_daily/weekly` | uses `volume_quote` not `volume` |

`fetch()` returns DataFrame with columns: symbol, date, open, high, low, close, [adj_close], volume, market, source

### Indicator System (`indicators/`)
**Registry pattern**: `@IndicatorRegistry.register` decorator on each class auto-registers it.

- **`BaseIndicator`**: Requires `required_columns()`, `warmup()` (historical rows needed), `compute()`
- **`IndicatorPipeline`** (`pipeline.py`): Orchestrates indicators from config; `to_long_dataframe()` converts results to (symbol, date, indicator, params_hash, value) long-form
- **Common indicators**: `SMA`, `EMA` in `indicators/common/`
- **IBD indicators** (`indicators/ibd/`): Cross-sectional; run via separate batch scripts, not per-symbol pipeline
  - `rs_rating.py`: IBD RS Rating (1–99 percentile), weights 40%/20%/20%/20% for 3/6/9/12m returns
  - `rs_line.py`: stock_close / benchmark_close ratio (KOSPI 1001 for KR, US500 for US)
  - `blue_dot.py`: RS Line at 52-week high while price is NOT at 52-week high → 1/0
- **Minervini** (`indicators/minervini/trend_template.py`): 8-condition screening; results in `minervini_screen_results_kr/us`

Indicators must be imported to register. Example in `daily_update.py`:
```python
from indicators.common import sma as _reg_sma  # noqa: F401
```

### Savers (`savers/`)
- **`IndicatorSaver`** (`savers/indicator_saver.py`): Wraps `DBManager.upsert_dataframe()` for indicator long-form storage. Currently supports long mode only (`save_long(df_long, mode)`). Used by daily/weekly update scripts after `IndicatorPipeline` produces results.

### Symbol Master System
Each market has a `*_symbol_master` table. Sync scripts (run weekly) compare FDR listing against DB, adding `ACTIVE` symbols and marking delisted as `DELISTED`.

Symbol loaders (`core/symbol_loader.py`, `core/us_symbol_loader.py`, `core/us_index_symbol_loader.py`, `core/kr_index_symbol_loader.py`, `core/crypto_symbol_loader.py`) provide `load_symbols_from_master()` — supports filtering by market and `--top N` by market cap.

### Core Utilities
- **`core/pykrx_adapter.py`**: Converts pykrx Korean-column responses (한글) to DataBatcher standard English format. Also handles date format conversion (YYYY-MM-DD ↔ YYYYMMDD).
- **`core/date_utils.py`**: Market calendar utilities (`DateUtils` class). Uses `pandas_market_calendars` for trading day calculations.
- **`core/fdr_sector_loader.py`**: Loads KRX-DESC sector/industry data from FDR `StockListing('KRX-DESC')`. Provides `sector_detail` (~162 subcategories) and `industry` fields for KR stocks.

### Weekly Aggregation (`core/weekly_aggregation.py`)
**Important contract**: `week_start` is the **first trading day** of the week, NOT a fixed Monday. `week_end` is the last trading day. Week key uses `date.to_period('W-FRI')`.

`aggregate_daily_to_weekly_trading_days(daily_df, skip_latest_week=True)` — `skip_latest_week=True` prevents writing incomplete current-week data.

### Bulk Price Loader (`core/bulk_price_loader.py`)
Used by IBD RS and Minervini scripts (cross-sectional computation):
- `load_all_prices_wide()`: Pivot table (dates × symbols) from DB
- `load_index_close()`: Benchmark index close prices
- `load_indicators_wide()`: Wide-format indicator data

### Daily Update Logic (`scripts/daily_update.py`)
Optimized incremental strategy:
1. Fetch 30 days price data from FDR → **INSERT ONLY** (preserve existing)
2. Load 250 days from DB for indicator calculation
3. Calculate all indicators for 250 days
4. Process dates **newest → oldest**: if `IndicatorChecker` reports all indicators complete → stop (early exit)

`IndicatorChecker` (`core/indicator_checker.py`) and `price_loader` (`core/price_loader.py`) are parameterized by `table` and `config_key` to support all markets.

## Configuration Structure (`config/settings.yaml`)

Indicator config sections (same pipeline structure, different target tables):
- `indicators` → `stock_indicators` (KR stocks daily)
- `indicators_us` → `us_stock_indicators` (US stocks daily)
- `indicators_kr_index` → `kr_index_indicators` (KR indices daily)
- `indicators_us_index` → `us_index_indicators` (US indices daily)
- `indicators_us_index_weekly` → `us_index_indicators_weekly`
- `indicators_crypto_daily` → `crypto_indicators_daily`
- `indicators_backfill` / `indicators_us_backfill` → for `backfill_indicators.py`
- `minervini_kr` / `minervini_us` → Minervini screening conditions

Market close times:
```yaml
markets:
  close_times:
    XKRX: "16:00"   # KST
    NYSE: "16:00"    # ET
  safe_delay_minutes: 30
```

Rate limiting: `runtime.rate_limit_per_sec: 5` (token bucket in `core/rate_limiter.py`).

## Database Schema (`db/init/01_schema.sql`)

All indicator tables use long-form: primary key `(symbol, date, indicator, params_hash)`.

| Market | Price table | Indicator table | Weekly price | Weekly indicator | Master |
|---|---|---|---|---|---|
| KR Stock | `stock_prices` | `stock_indicators` | `stock_prices_weekly` | `stock_indicators_weekly` | `symbol_master` |
| KR Index | `kr_index_prices` | `kr_index_indicators` | `kr_index_prices_weekly` | `kr_index_indicators_weekly` | `kr_index_master` |
| US Stock | `us_stock_prices` | `us_stock_indicators` | `us_stock_prices_weekly` | `us_stock_indicators_weekly` | `us_symbol_master` |
| US Index | `us_index_prices` | `us_index_indicators` | `us_index_prices_weekly` | `us_index_indicators_weekly` | `us_index_master` |
| Crypto | `crypto_prices_daily` | `crypto_indicators_daily` | `crypto_prices_weekly` | `crypto_indicators_weekly` | `crypto_symbol_master` |

Screening: `minervini_screen_results_kr`, `minervini_screen_results_us`

**Key differences**:
- Index tables: no `adj_close`
- Crypto: `volume_quote` instead of `volume`; weekly `week_start` = UTC Monday
- `symbol_master` / `us_symbol_master`: has `symbol_type` (STOCK/ETF), sector/industry columns; ETF rows always have NULL sector

DB migrations: `apps/ingest-databatcher/scripts/migrations/`

## Key Design Patterns

### Indicator Parameter Hashing (`core/params.py`)
Each indicator config is hashed so multiple variants coexist in the same table:
- `sma(window=5, column=close)` → hash1
- `sma(window=20, column=close)` → hash2

### Warmup Period
Each indicator reports `warmup()` days. Pipeline takes the max. Data fetching goes back warmup days to ensure valid output from day 1 of the target range.

### Indicator Index
Indicators expect DataFrame with **DatetimeIndex**. Scripts convert the date column to index before calling the pipeline.

## Adding New Indicators

1. Create `indicators/common/my_indicator.py`
2. Inherit `BaseIndicator`, implement `required_columns()`, `warmup()`, `compute()`
3. Add `@IndicatorRegistry.register` decorator
4. Import it in the relevant update script to auto-register
5. Add entry to the relevant `indicators.pipeline` section in `settings.yaml`

## Production Cron Schedule

```bash
# KR — daily (16:30 KST)
30 16 * * 1-5  python apps/ingest-databatcher/scripts/daily_update.py --all --force
35 16 * * 1-5  python apps/ingest-databatcher/scripts/kr_rs_update.py --force
40 16 * * 1-5  python apps/ingest-databatcher/scripts/kr_minervini_update.py --days 7 --force

# KR — weekly (Sunday 02:00 KST)
0 2 * * 0  python apps/ingest-databatcher/scripts/sync_symbol_master.py
0 2 * * 0  python apps/ingest-databatcher/scripts/kr_index_sync_master.py
30 2 * * 0 python apps/ingest-databatcher/scripts/weekly_update.py --all
30 2 * * 0 python apps/ingest-databatcher/scripts/kr_index_weekly_update.py --all

# US — daily (22:00 KST = 16:00 ET + 30 min)
0 22 * * 1-5  python apps/ingest-databatcher/scripts/us_index_daily_update.py --all --force
0 22 * * 1-5  python apps/ingest-databatcher/scripts/us_daily_update.py --all --with-indicators
5 7  * * 2-6  python apps/ingest-databatcher/scripts/us_rs_update.py --force
10 7 * * 2-6  python apps/ingest-databatcher/scripts/us_minervini_update.py --days 7 --force

# US — weekly (Saturday KST)
0 10 * * 6  python apps/ingest-databatcher/scripts/us_weekly_update.py --all
0 10 * * 6  python apps/ingest-databatcher/scripts/us_index_weekly_update.py --all
0 2  * * 0  python apps/ingest-databatcher/scripts/us_sync_symbol_master.py
0 2  * * 0  python apps/ingest-databatcher/scripts/us_index_sync_master.py

# Crypto — daily
0 8 * * *  python apps/ingest-databatcher/scripts/crypto_daily_update.py --all --with-indicators
# Crypto — weekly
0 9 * * 6  python apps/ingest-databatcher/scripts/crypto_weekly_update.py --all
0 2 * * 0  python apps/ingest-databatcher/scripts/crypto_sync_symbol_master.py
```