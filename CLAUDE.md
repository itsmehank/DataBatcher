# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DataBatcher is a multi-market stock data collection and technical indicator calculation system. It supports Korean (KRX), US (NYSE/NASDAQ), and Crypto (Binance) markets. It fetches price data from various sources (pykrx, FinanceDataReader, Binance API), computes technical indicators (SMA, EMA, etc.), and stores everything in MySQL for analysis and trading strategy backtesting.

**Supported Markets**:
- **Korean (KRX)**: KOSPI, KOSDAQ, KONEX, ETF via pykrx
- **US**: NYSE, NASDAQ, US ETF via FinanceDataReader
- **Crypto**: Binance Spot (USDT pairs) via Binance API

**Core Pipeline**: Data Collection (collectors) → Indicator Calculation (indicators) → Database Storage (savers)

## Development Commands

### Environment Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Set up local MySQL with Docker
# docker ps를 통해 실행중인 mysql을 확인할 수 있다.
docker ps
# 실행중인 mysql의 이름은 grafana-with-db-mysql 이다. 만약 해당 이미지가 실행중이 아니면 사용자에게 해당 이미지 실행을 요청한다.
# mysql의 계정 정보는 .env 파일에 작성되어 있다. 이를 참고한다.

# Initialize database schema
python apps/ingest-databatcher/scripts/init_db.py
```

### Initial Setup Guide (처음 시작하기)

DataBatcher를 처음 설치하고 실행하는 순서입니다. 각 단계를 순서대로 진행하세요.

#### Step 1: 환경 설정 및 검증 (Environment Setup)

```bash
# 1-1. 가상환경 활성화 (이미 되어있으면 스킵)
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows

# 1-2. 의존성 설치
pip install -r requirements.txt

# 1-3. Docker로 MySQL 실행 (로컬 개발 환경)
docker compose -f db/compose/mysql-standalone/docker-compose-mysql.yaml up -d

# 1-4. 데이터베이스 초기화 (테이블 생성)
python apps/ingest-databatcher/scripts/init_db.py

# 1-5. 설정 파일 확인
# apps/ingest-databatcher/config/settings.yaml 파일이 존재하는지 확인
# DATABASE_URL 환경변수 또는 database.url 설정 확인
cat apps/ingest-databatcher/config/settings.yaml

# 1-6. 데이터베이스 연결 테스트
PYTHONPATH=apps/ingest-databatcher python -c "from core.config_loader import load_settings; from core.db_manager import DBManager, DBConfig; cfg = load_settings(); db_cfg = DBConfig(**cfg['database']); engine = DBManager.get_engine(db_cfg); print('✓ DB 연결 성공')"
```

**예상 소요 시간**: 5-10분

---

#### Step 2: 종목 마스터 동기화 (Symbol Master Sync)

**목적**: KRX에 상장된 모든 종목 정보를 `symbol_master` 테이블에 저장

```bash
# 2-1. 종목 마스터 동기화 실행
python apps/ingest-databatcher/scripts/sync_symbol_master.py

# 예상 결과:
# - KOSPI: ~950개 종목
# - KOSDAQ: ~1,700개 종목
# - KONEX: ~100개 종목
# - 총 약 2,900개 종목 추가됨
```

**예상 소요 시간**: 1-2분

**확인 방법**:
```bash
# MySQL에서 확인
mysql -h 127.0.0.1 -u YOUR_DB_USER -p market -e "SELECT COUNT(*) as total, market, status FROM symbol_master GROUP BY market, status;"

# 또는 Python으로 확인
PYTHONPATH=apps/ingest-databatcher python -c "from core.config_loader import load_settings; from core.db_manager import DBManager, DBConfig; from sqlalchemy import text; cfg = load_settings(); db_cfg = DBConfig(**cfg['database']); engine = DBManager.get_engine(db_cfg); with engine.connect() as conn: result = conn.execute(text('SELECT COUNT(*) FROM symbol_master WHERE status=\"ACTIVE\"')); print(f'ACTIVE 종목 수: {result.scalar()}')"
```

---

#### Step 3: 과거 데이터 대량 수집 (Bulk Collection)

**목적**: 모든 종목의 과거 가격 데이터와 지표를 수집

**주의사항**:
- 이 단계는 **시간이 오래 걸립니다** (전체 종목 수집 시 10-30분)
- FDR API 제약으로 인해 rate limiting이 적용됩니다
- 실패한 종목은 `logs/bulk_update_failed.log`에 기록됩니다

**옵션별 실행 방법**:

```bash
# 3-1. 전체 종목, 최근 1년 수집 (추천)
python apps/ingest-databatcher/scripts/bulk_update.py \
  --start 2024-01-01 \
  --end 2024-12-31 \
  --workers 4

# 3-2. KOSPI만 수집 (빠른 테스트용)
python apps/ingest-databatcher/scripts/bulk_update.py \
  --start 2024-01-01 \
  --end 2024-12-31 \
  --market KOSPI \
  --workers 4

# 3-3. 시가총액 상위 100개만 수집 (프로토타입용)
python apps/ingest-databatcher/scripts/bulk_update.py \
  --start 2024-01-01 \
  --end 2024-12-31 \
  --top 100 \
  --workers 4

# 3-4. 전체 종목, 5년치 수집 (프로덕션 권장)
python apps/ingest-databatcher/scripts/bulk_update.py \
  --start 2020-01-01 \
  --end 2024-12-31 \
  --workers 8
```

**workers 수 조정 가이드**:
- `--workers 4`: 안정적 (추천)
- `--workers 8`: 빠름 (네트워크 양호 시)
- `--workers 16`: 매우 빠름 (rate limit 주의)

**예상 소요 시간**:
- 상위 100개, 1년: 2-3분
- KOSPI 전체, 1년: 5-8분
- 전체 종목, 1년: 10-15분
- 전체 종목, 5년: 20-30분

**진행 상황 모니터링**:
```
Collecting: 45%|████████          | 1234/2894 [05:23<06:12, 4.46symbol/s]
```

**확인 방법**:
```bash
# 수집된 데이터 확인
mysql -h 127.0.0.1 -u YOUR_DB_USER -p market -e "
  SELECT
    COUNT(DISTINCT symbol) as symbols,
    COUNT(*) as price_rows,
    MIN(date) as oldest,
    MAX(date) as newest
  FROM stock_prices;
"

# 지표 데이터 확인
mysql -h 127.0.0.1 -u YOUR_DB_USER -p market -e "
  SELECT
    indicator,
    COUNT(*) as rows
  FROM stock_indicators
  GROUP BY indicator;
"
```

**실패 처리**:
```bash
# 실패한 종목 확인
cat logs/bulk_update_failed.log

# 실패한 종목만 재시도 (수동)
# failed.log에서 심볼 리스트 추출 후
python apps/ingest-databatcher/scripts/daily_update.py --symbols 005930 000660 ... --force
```

---

#### Step 4: 일일 업데이트 테스트 (Daily Update Test)

**목적**: 일일 업데이트가 정상 동작하는지 확인

```bash
# 4-1. 전체 종목 업데이트 테스트 (강제 실행)
python apps/ingest-databatcher/scripts/daily_update.py --all --force

# 4-2. 특정 마켓만 업데이트 테스트
python apps/ingest-databatcher/scripts/daily_update.py --all --market KOSPI --force

# 4-3. 소수 종목만 테스트
python apps/ingest-databatcher/scripts/daily_update.py --all --top 10 --force
```

**예상 소요 시간**:
- 상위 10개: 1-2분
- KOSPI 전체: 10-15분
- 전체 종목: 20-30분

**동작 확인**:
- 각 종목마다 "가격 X건 신규 추가" 메시지
- 각 종목마다 "Y개 날짜 처리, 지표 Z건 업서트" 메시지
- 이미 최신 데이터가 있으면 "모든 지표 완료 → 중단" 메시지

---

#### Step 5: 자동화 설정 (Optional, Production)

**Cron 설정 예시** (Linux/Mac):

```bash
# crontab 편집
crontab -e

# 추가할 내용:
# 주간: 일요일 새벽 2시에 종목 마스터 동기화
0 2 * * 0 cd /path/to/DataBatcher && source .venv/bin/activate && python apps/ingest-databatcher/scripts/sync_symbol_master.py >> logs/sync_symbol_master.log 2>&1

# 일일: 평일 오후 5시(장마감 30분 후)에 전체 업데이트
0 17 * * 1-5 cd /path/to/DataBatcher && source .venv/bin/activate && python apps/ingest-databatcher/scripts/daily_update.py --all --force >> logs/daily_update.log 2>&1
```

**Windows Task Scheduler**:
1. 작업 스케줄러 실행
2. "기본 작업 만들기" 선택
3. 트리거: 매일 또는 매주
4. 동작: 프로그램 시작
   - 프로그램: `python.exe`
   - 인수: `apps/ingest-databatcher/scripts/daily_update.py --all --force`
   - 시작 위치: `C:\path\to\DataBatcher`

---

### Quick Start (빠른 시작)

최소한의 설정으로 빠르게 시작하기:

```bash
# 1. DB 초기화
docker compose -f db/compose/mysql-standalone/docker-compose-mysql.yaml up -d
python apps/ingest-databatcher/scripts/init_db.py

# 2. 종목 동기화
python apps/ingest-databatcher/scripts/sync_symbol_master.py

# 3. 상위 100개 종목만 최근 1년 데이터 수집 (테스트)
python apps/ingest-databatcher/scripts/bulk_update.py --start 2024-01-01 --end 2024-12-31 --top 100 --workers 4

# 4. 일일 업데이트 테스트
python apps/ingest-databatcher/scripts/daily_update.py --all --top 10 --force
```

**예상 소요 시간**: 5-10분

---

### Running the System (정규 운영)

#### Sync Symbol Master (Weekly)
```bash
# Sync all KRX symbols from FDR to symbol_master table
python apps/ingest-databatcher/scripts/sync_symbol_master.py
```

#### Bulk Collection (Initial Setup or Backfill)
```bash
# Collect all symbols for past 5 years
python apps/ingest-databatcher/scripts/bulk_update.py --start 2020-01-01 --end 2024-12-31 --workers 8

# Or collect only KOSPI symbols
python apps/ingest-databatcher/scripts/bulk_update.py --start 2023-01-01 --end 2024-12-31 --market KOSPI

# Or top 100 symbols by market cap
python apps/ingest-databatcher/scripts/bulk_update.py --start 2024-01-01 --end 2024-12-31 --top 100
```

#### Daily Updates
```bash
# Update all ACTIVE symbols (recommended)
python apps/ingest-databatcher/scripts/daily_update.py --all --force

# Or specific market only
python apps/ingest-databatcher/scripts/daily_update.py --all --market KOSPI --force

# Or specific symbols (legacy mode)
python apps/ingest-databatcher/scripts/daily_update.py --symbols 005930 000660 --force
```

#### Development/Testing
```bash
# Probe FDR data source (Korean)
python apps/ingest-databatcher/scripts/probes/fdr_stock_probe.py --symbol 005930 --start 2020-01-01 --end 2020-12-31

# Probe FDR US stock data source
python apps/ingest-databatcher/scripts/probes/fdr_us_stock_probe.py --symbol AAPL --start 2024-01-01 --end 2024-01-31
```

### US Stock Commands

#### Sync US Symbol Master (Weekly)
```bash
# Sync all NYSE/NASDAQ/ETF symbols to us_symbol_master table (with yfinance sector enrichment)
python apps/ingest-databatcher/scripts/us_sync_symbol_master.py

# Sync specific market only
python apps/ingest-databatcher/scripts/us_sync_symbol_master.py --market NASDAQ

# Skip yfinance sector enrichment (faster)
python apps/ingest-databatcher/scripts/us_sync_symbol_master.py --skip-yfinance

# Limit yfinance calls (e.g., first 100 symbols only)
python apps/ingest-databatcher/scripts/us_sync_symbol_master.py --yfinance-limit 100

# Adjust yfinance rate limit (default 2.0 req/sec)
python apps/ingest-databatcher/scripts/us_sync_symbol_master.py --yfinance-rate 3.0
```

#### US Bulk Collection (Initial Setup)
```bash
# Collect all US symbols for past 1 year
python apps/ingest-databatcher/scripts/us_bulk_update.py --start 2024-01-01 --end 2024-12-31 --workers 4

# NASDAQ only with indicators
python apps/ingest-databatcher/scripts/us_bulk_update.py --start 2024-01-01 --end 2024-12-31 --market NASDAQ --with-indicators

# Top 100 US symbols
python apps/ingest-databatcher/scripts/us_bulk_update.py --start 2024-01-01 --end 2024-12-31 --top 100 --with-indicators
```

#### US Daily Updates
```bash
# Update all ACTIVE US symbols
python apps/ingest-databatcher/scripts/us_daily_update.py --all --with-indicators

# Specific market only
python apps/ingest-databatcher/scripts/us_daily_update.py --all --market NASDAQ --with-indicators

# Specific symbols
python apps/ingest-databatcher/scripts/us_daily_update.py --symbols AAPL MSFT GOOGL --with-indicators
```

#### US Weekly Bulk Collection (Initial Setup)
```bash
# Collect all US symbols weekly data (DB full period)
python apps/ingest-databatcher/scripts/us_bulk_update_weekly.py

# NASDAQ only
python apps/ingest-databatcher/scripts/us_bulk_update_weekly.py --market NASDAQ

# Top 100 US symbols, specific period
python apps/ingest-databatcher/scripts/us_bulk_update_weekly.py --start 2020-01-01 --end 2024-12-31 --top 100
```

#### US Weekly Updates
```bash
# Update all ACTIVE US symbols weekly data
python apps/ingest-databatcher/scripts/us_weekly_update.py --all

# Specific market only
python apps/ingest-databatcher/scripts/us_weekly_update.py --all --market NASDAQ

# Specific symbols
python apps/ingest-databatcher/scripts/us_weekly_update.py --symbols AAPL MSFT GOOGL
```

### US Index Commands

#### Sync US Index Master (Weekly)
```bash
# Sync S&P 500, Dow Jones, NASDAQ Composite to us_index_master table
python apps/ingest-databatcher/scripts/us_index_sync_master.py
```

#### US Index Bulk Collection (Initial Setup)
```bash
# Collect all US indices for past 5 years
python apps/ingest-databatcher/scripts/us_index_bulk_update.py --start 2020-01-01 --end 2024-12-31

# S&P 500 only
python apps/ingest-databatcher/scripts/us_index_bulk_update.py --start 2024-01-01 --end 2024-12-31 --market SP500
```

#### US Index Daily Updates
```bash
# Update all ACTIVE US indices
python apps/ingest-databatcher/scripts/us_index_daily_update.py --all --force

# Specific market only
python apps/ingest-databatcher/scripts/us_index_daily_update.py --all --market SP500 --force

# Specific indices
python apps/ingest-databatcher/scripts/us_index_daily_update.py --symbols US500 DJI --force
```

#### US Index Weekly Bulk Collection (Initial Setup)
```bash
# Collect all US indices weekly data (DB full period)
python apps/ingest-databatcher/scripts/us_index_bulk_update_weekly.py

# Specific period
python apps/ingest-databatcher/scripts/us_index_bulk_update_weekly.py --start 2020-01-01 --end 2024-12-31

# S&P 500 only
python apps/ingest-databatcher/scripts/us_index_bulk_update_weekly.py --market SP500
```

#### US Index Weekly Updates
```bash
# Update all ACTIVE US indices weekly data
python apps/ingest-databatcher/scripts/us_index_weekly_update.py --all

# Specific market only
python apps/ingest-databatcher/scripts/us_index_weekly_update.py --all --market SP500

# Specific indices
python apps/ingest-databatcher/scripts/us_index_weekly_update.py --symbols US500 DJI
```

### IBD RS / RS Line / Blue Dot Commands

#### KR Stock RS Indicators
```bash
# Calculate RS indicators for all KR stocks (after daily_update)
python apps/ingest-databatcher/scripts/kr_rs_update.py --force

# Specific market, last 5 days
python apps/ingest-databatcher/scripts/kr_rs_update.py --market KOSPI --days 5 --force

# Include stocks with less than 12 months data
python apps/ingest-databatcher/scripts/kr_rs_update.py --no-strict-12m --force
```

#### US Stock RS Indicators
```bash
# Calculate RS indicators for all US stocks (after us_daily_update)
python apps/ingest-databatcher/scripts/us_rs_update.py --force

# Specific market, last 5 days
python apps/ingest-databatcher/scripts/us_rs_update.py --market NASDAQ --days 5 --force

# Include stocks with less than 12 months data
python apps/ingest-databatcher/scripts/us_rs_update.py --no-strict-12m --force
```

### Minervini Trend Template Screening

```bash
# 한국 주식 - 전체 백필
python apps/ingest-databatcher/scripts/kr_minervini_update.py --days 9999 --force

# 한국 주식 - 최근 7일
python apps/ingest-databatcher/scripts/kr_minervini_update.py --days 7 --force

# 특정 마켓만 (KOSPI/KOSDAQ/ETF)
python apps/ingest-databatcher/scripts/kr_minervini_update.py --market KOSPI --days 30 --force

# 미국 주식 - 전체 백필
python apps/ingest-databatcher/scripts/us_minervini_update.py --days 9999 --force

# 미국 주식 - 최근 7일
python apps/ingest-databatcher/scripts/us_minervini_update.py --days 7 --force

# 특정 마켓만 (NYSE/NASDAQ/ETF)
python apps/ingest-databatcher/scripts/us_minervini_update.py --market NASDAQ --days 30 --force
```

### Indicator Backfill (Independent Indicator Calculation)

```bash
# 한국 주식 전체 백필 (DB 가격 데이터 → 지표 계산)
python apps/ingest-databatcher/scripts/backfill_indicators.py --source stock_prices

# 미국 주식, NASDAQ만
python apps/ingest-databatcher/scripts/backfill_indicators.py --source us_stock_prices --market NASDAQ

# 특정 종목만
python apps/ingest-databatcher/scripts/backfill_indicators.py --source stock_prices --symbols 005930 000660

# 병렬 워커 수 지정
python apps/ingest-databatcher/scripts/backfill_indicators.py --source us_stock_prices --workers 8

# 기존 지표 덮어쓰기 (재계산)
python apps/ingest-databatcher/scripts/backfill_indicators.py --source stock_prices --mode upsert
```

### Test Environment

```bash
# 테스트 DB (trade_test) 초기화
python apps/ingest-databatcher/scripts/init_test_db.py
```

### Testing
There is currently no formal test suite. Testing is done via probe scripts in `apps/ingest-databatcher/scripts/probes/`.

## High-Level Architecture

### Configuration System (apps/ingest-databatcher/core/config_loader.py)
Loads settings with the following precedence:
1. Environment variable `DATABASE_URL` (highest priority, overrides database.url)
2. `apps/ingest-databatcher/config/settings.dev.yaml` (development overlay)
3. `apps/ingest-databatcher/config/settings.yaml` (base configuration)

Configuration is merged hierarchically using `merge_dict()`. All scripts use `load_settings()` to access configuration.

### Database Layer (apps/ingest-databatcher/core/db_manager.py)
- **DBManager**: Singleton-style SQLAlchemy engine manager
- **Key Methods**:
  - `get_engine()`: Returns shared engine instance (creates on first call)
  - `get_latest_date()`: Finds the most recent date for a symbol/table (used for incremental updates)
  - `upsert_dataframe()`: Bulk upsert using MySQL's `ON DUPLICATE KEY UPDATE`
- Connection pool configured via `DBConfig` dataclass (pool_size, max_overflow, pool_recycle, pool_pre_ping)

### Collector Pattern (apps/ingest-databatcher/core/base_collector.py + apps/ingest-databatcher/collectors/)
- **BaseCollector**: Abstract base for all data collectors
- **KRStockCollector** (apps/ingest-databatcher/collectors/kr_stock.py): Fetches Korean stock data via pykrx
  - `fetch()`: Returns DataFrame with columns: symbol, date, open, high, low, close, adj_close, volume, market, source
  - `validate()`: Validates data (inherited from BaseCollector)
  - `save()`: Upserts data to `stock_prices` table via DBManager
- **USStockCollector** (apps/ingest-databatcher/collectors/us_stock.py): Fetches US stock data via FinanceDataReader
  - `fetch()`: Returns DataFrame with same columns as KRStockCollector
  - `save()`: Upserts data to `us_stock_prices` table

### Indicator System (apps/ingest-databatcher/indicators/)
**Registry Pattern**: All indicators register themselves via `@IndicatorRegistry.register` decorator

- **BaseIndicator**: Abstract base requiring:
  - `required_columns()`: List of DataFrame columns needed
  - `warmup()`: Number of historical days required (e.g., SMA(20) needs 20 days warmup)
  - `compute()`: Returns pd.Series or dict[str, pd.Series] with calculated values

- **IndicatorPipeline** (apps/ingest-databatcher/indicators/pipeline.py):
  - Orchestrates multiple indicators from config (`indicators.pipeline` in YAML)
  - `warmup_days()`: Calculates max warmup across all indicators
  - `run()`: Executes all indicators and returns dict of Series
  - `to_long_dataframe()`: Transforms results to long-form table schema (symbol, date, indicator, params_hash, value)

- **Existing Indicators**:
  - `SMA` (apps/ingest-databatcher/indicators/common/sma.py): Simple Moving Average
  - `EMA` (apps/ingest-databatcher/indicators/common/ema.py): Exponential Moving Average

### Symbol Master System (NEW)
**Purpose**: Centralized symbol management for automated collection

- **scripts/sync_symbol_master.py**: Syncs all KRX symbols from FDR
  - Adds new listings (status=ACTIVE)
  - Marks delisted symbols (status=DELISTED)
  - Updates metadata (name, market cap)
  - Run weekly to keep symbol list current

- **apps/ingest-databatcher/core/symbol_loader.py**: Common utilities for loading symbols
  - `load_symbols_from_master()`: Load ACTIVE symbols by criteria
  - Supports filtering by market (KOSPI/KOSDAQ)
  - Supports top N by market cap

### IBD RS / RS Line / Blue Dot System
**Cross-sectional indicators** that require all-symbol data, implemented as separate batch scripts rather than per-symbol pipeline.

- **apps/ingest-databatcher/indicators/ibd/rs_rating.py**: IBD RS Rating calculation (1~99 percentile)
  - `calculate_ibd_rs_rating()`: 3/6/9/12 month return weighted sum → cross-sectional rank
  - Weights: 40% 3m + 20% 6m + 20% 9m + 20% 12m (configurable)
  - strict_12m option: exclude stocks with < 12 months data

- **apps/ingest-databatcher/indicators/ibd/rs_line.py**: RS Line calculation
  - `calculate_rs_line_bulk()`: stock_close / index_close ratio (vectorized)
  - Benchmark: KOSPI(1001) for KR, S&P 500(US500) for US

- **apps/ingest-databatcher/indicators/ibd/blue_dot.py**: Blue Dot Signal
  - `calculate_blue_dot_bulk()`: RS Line 52-week high AND price NOT 52-week high → 1/0

- **apps/ingest-databatcher/core/bulk_price_loader.py**: Utilities for loading all-symbol data in wide format
  - `load_all_prices_wide()`: Pivot table (dates x symbols) for cross-sectional computation
  - `load_index_close()`: Benchmark index close prices

- **scripts/kr_rs_update.py**: KR stock RS batch (→ stock_indicators INSERT ONLY)
- **scripts/us_rs_update.py**: US stock RS batch (→ us_stock_indicators INSERT ONLY)

- **Storage**: Reuses existing indicator tables (long-form), params_hash for deduplication
  - `ibd_rs_rating` → `params_hash("ibd_rs_rating", {"strict_12m": true})`
  - `rs_line` → `params_hash("rs_line", {"benchmark": "1001"})` (KR) / `{"benchmark": "US500"}` (US)
  - `blue_dot` → `params_hash("blue_dot", {"lookback": 252, "benchmark": "..."})`

### Bulk Collection System (NEW)
**scripts/bulk_update.py**: Parallel collection for all symbols

- **Features**:
  - Multi-threaded collection with rate limiting
  - Progress bar (tqdm) for monitoring
  - Failed symbols logged to `logs/bulk_update_failed.log`
  - Configurable workers and market filters

- **Rate Limiting**: Uses `apps/ingest-databatcher/core/rate_limiter.py` to prevent FDR API blocking
  - Thread-safe token bucket algorithm
  - Configurable via `runtime.rate_limit_per_sec` in settings

- **Usage Pattern**:
  1. Initial: `bulk_update.py` for historical data (10-20 min for all symbols)
  2. Daily: `daily_update.py --all` for incremental updates (15-20 min)

### Database Schema (docker/mysql/init/01_schema.sql)

**Korean Stock Tables**:
- **stock_prices**: Primary key (symbol, date), stores OHLCV data
- **stock_indicators**: Primary key (symbol, date, indicator, params_hash), stores calculated indicators in long-form
- **symbol_master**: Symbol metadata, status tracking (ACTIVE/DELISTED), sector info (pykrx 대분류 + FDR 세분류 + industry)

**US Stock Tables**:
- **us_stock_prices**: Primary key (symbol, date), stores US stock OHLCV data
- **us_stock_indicators**: Primary key (symbol, date, indicator, params_hash), stores US stock indicators in long-form
- **us_symbol_master**: US symbol metadata (NYSE/NASDAQ/ETF, status tracking, sector/industry via FDR + yfinance)

**US Index Tables**:
- **us_index_prices**: Primary key (symbol, date), stores US index OHLCV data (no adj_close)
- **us_index_indicators**: Primary key (symbol, date, indicator, params_hash), stores US index indicators in long-form
- **us_index_prices_weekly**: Primary key (symbol, week_start), US index weekly OHLCV (no adj_close)
- **us_index_indicators_weekly**: Primary key (symbol, week_start, indicator, params_hash), US index weekly indicators in long-form
- **us_index_master**: US index metadata (SP500/DJI/IXIC, status tracking)

**Crypto Tables**:
- **crypto_prices_daily**: Binance spot daily OHLCV (symbol, date)
- **crypto_indicators_daily**: Crypto indicators in long-form
- **crypto_symbol_master**: Crypto trading pairs metadata

**Common Tables**:
- **sync_log**: ETL job execution tracking (planned for future use)

### Scripts Workflow

**scripts/sync_symbol_master.py** (weekly maintenance):
1. Fetch all KRX symbols from FDR via `StockListing('KRX')`
2. Compare with existing symbols in DB
3. Add new symbols (status=ACTIVE)
4. Update existing symbols (name, market)
5. Mark delisted symbols (status=DELISTED)

**scripts/bulk_update.py** (initial data load):
1. Load ACTIVE symbols from symbol_master (filtered by market/top N)
2. Create thread pool with N workers
3. For each symbol (in parallel):
   - Acquire rate limit token
   - Fetch price data → Validate → Save
   - Calculate indicators → Transform to long-form → Save
4. Display progress bar and summary statistics
5. Log failed symbols to `logs/bulk_update_failed.log`

**scripts/daily_update.py** (daily incremental updates - OPTIMIZED as of 2026-01-19):
1. Load configuration and initialize DB engine
2. Check if market is closed + buffer period (unless `--force`)
3. Determine symbol list:
   - If `--all`: Load from symbol_master (filtered by market/top)
   - Else: Use `--symbols` argument
4. For each symbol (sequential, via `process_symbol()`):
   - **STEP 1**: Fetch 30 days of price data from FDR → INSERT ONLY (preserves existing)
   - **STEP 2**: Load 250 days of price data from DB
   - **STEP 3**: Calculate indicators for all 250 days (with warmup period)
   - **STEP 4**: Process dates in reverse order (newest → oldest):
     - Check if all indicators complete for the date (`IndicatorChecker`)
     - If complete: stop processing (early exit)
     - If incomplete: UPSERT indicators for that date only
     - Continue to next older date

### US Stock Scripts Workflow

**scripts/us_sync_symbol_master.py** (weekly maintenance):
1. Fetch NYSE symbols from FDR via `StockListing('NYSE')`
2. Fetch NASDAQ symbols from FDR via `StockListing('NASDAQ')`
3. Fetch ETF symbols from FDR via `StockListing('ETF/US')`
4. Compare with existing symbols in us_symbol_master
5. Add new symbols (status=ACTIVE), update existing, mark delisted

**scripts/us_bulk_update.py** (initial data load):
1. Load ACTIVE symbols from us_symbol_master (filtered by market/top N)
2. Create thread pool with N workers
3. For each symbol (in parallel):
   - Acquire rate limit token
   - Fetch price data via FDR → Validate → Save (INSERT ONLY)
   - Calculate indicators → Transform to long-form → Save
4. Display progress bar and summary statistics
5. Log failed symbols to `logs/us_bulk_update_failed.log`

**scripts/us_daily_update.py** (daily incremental updates):
1. Check if US market is closed (16:00 ET + safe_delay)
2. Determine symbol list (--all or --symbols)
3. For each symbol:
   - Fetch 50 days of price data → INSERT ONLY
   - Calculate indicators (with warmup)
   - Save indicators → INSERT ONLY

### US Index Scripts Workflow

**scripts/us_index_sync_master.py** (weekly maintenance):
1. Hardcoded 3 US indices: US500 (S&P 500), DJI (Dow Jones), IXIC (NASDAQ Composite)
2. UPSERT to `us_index_master` (names are hardcoded, FDR has no index name API)

**scripts/us_index_bulk_update.py** (initial data load):
1. Load ACTIVE indices from us_index_master (filtered by market)
2. For each index (sequential, only 3 indices):
   - Fetch price data via FDR → Validate → Save (INSERT ONLY)
   - Calculate indicators (SMA 5/20/40) → Transform to long-form → Save (INSERT ONLY)
3. Display summary statistics

**scripts/us_index_daily_update.py** (daily incremental updates):
1. Check if US market is closed (16:00 ET + safe_delay)
2. Determine index list (--all or --symbols)
3. For each index:
   - Fetch 50 days of price data → INSERT ONLY
   - Load 250 days from DB → Calculate indicators with warmup
   - Process dates in reverse order → IndicatorChecker early exit
   - Save indicators → INSERT ONLY

**scripts/us_index_bulk_update_weekly.py** (initial weekly data load):
1. Load ACTIVE indices from us_index_master (filtered by market)
2. For each index (sequential, only 3 indices):
   - Query daily data from us_index_prices (no adj_close)
   - Aggregate to weekly via `aggregate_daily_to_weekly_trading_days(skip_latest_week=True)`
   - Save weekly prices INSERT ONLY to `us_index_prices_weekly`
   - Calculate indicators (SMA 5/20/40) → Save INSERT ONLY to `us_index_indicators_weekly`
3. Display summary statistics

**scripts/us_index_weekly_update.py** (weekly incremental updates):
1. Determine index list (--all or --symbols)
2. For each index:
   - Load 250 weeks of daily data from us_index_prices
   - Aggregate to weekly (skip_latest_week based on ET weekday)
   - Save weekly prices INSERT ONLY to `us_index_prices_weekly`
   - Calculate indicators with warmup
   - Process weeks in reverse order → check `us_index_indicators_weekly` completeness → early exit
   - Save indicators INSERT ONLY

## Key Design Patterns

### Warmup Period Handling
Indicators need historical data to produce valid values (e.g., SMA(20) needs 20 prior days). The system:
1. Each indicator reports its `warmup()` requirement
2. Pipeline calculates `warmup_days()` as max across all indicators
3. When fetching data, start date is adjusted backward by warmup period
4. All data is stored, including warmup period rows (values may be NaN during warmup)

### Incremental Updates
`DBManager.get_latest_date()` finds the most recent stored date for a symbol. Daily updates fetch from (latest_date - warmup) to ensure indicators recalculate correctly with overlapping data.

### Indicator Parameter Hashing (apps/ingest-databatcher/core/params.py)
Each indicator configuration is hashed (params_hash) so multiple variants can coexist:
- `sma(window=5, column=close)` → hash1
- `sma(window=20, column=close)` → hash2

This enables storing multiple parameter sets for the same indicator in `stock_indicators` table.

### Plugin-Style Indicator Registration
Import indicator modules to auto-register them:
```python
from indicators.common import sma as _reg_sma  # noqa: F401
from indicators.common import ema as _reg_ema  # noqa: F401
```
The `@IndicatorRegistry.register` decorator adds them to the global registry.

## Configuration Structure

### indicators.pipeline (apps/ingest-databatcher/config/settings.yaml)
Defines which indicators to calculate and their parameters:
```yaml
indicators:
  pipeline:
    - name: sma
      params: { window: 5, column: close }
      save: true
    - name: ema
      params: { window: 12, column: close }
      save: true
```

### markets.close_times
Used by `date_utils.py` to determine if market is closed before running updates:
```yaml
markets:
  close_times:
    XKRX: "16:00"  # Korean exchange
    NYSE: "16:00"  # US exchange (Eastern Time)
  safe_delay_minutes: 30  # Buffer after close
```

### indicators_us (apps/ingest-databatcher/config/settings.yaml)
US stock-specific indicator pipeline (same structure as `indicators`):
```yaml
indicators_us:
  materialization:
    mode: long
    table_long: us_stock_indicators
  pipeline:
    - name: sma
      params: { window: 5, column: close }
      save: true
    - name: sma
      params: { window: 20, column: close }
      save: true
    - name: ema
      params: { window: 12, column: close }
      save: true
    - name: ema
      params: { window: 26, column: close }
      save: true
```

## Adding New Indicators

1. Create new file in `apps/ingest-databatcher/indicators/common/` (e.g., `rsi.py`)
2. Inherit from `BaseIndicator` and implement required methods
3. Add `@IndicatorRegistry.register` decorator
4. Import in `apps/ingest-databatcher/scripts/daily_update.py` to register
5. Add to `indicators.pipeline` in config YAML

Example skeleton:
```python
@IndicatorRegistry.register
class RSI(BaseIndicator):
    name = "rsi"

    def required_columns(self, p: IndicatorParams) -> list[str]:
        return ["close"]

    def warmup(self, p: IndicatorParams) -> int:
        return int(p.params.get("window", 14)) * 2

    def compute(self, df: pd.DataFrame, p: IndicatorParams) -> pd.Series:
        # Calculate RSI
        pass
```

## Important Implementation Notes

- **Character Encoding**: All database tables use `utf8mb4` charset. Ensure `DATABASE_URL` includes `?charset=utf8mb4`
- **Date Handling**: Dates are stored as `DATE` type (not datetime). Use `pd.to_datetime(...).dt.date` when saving
- **Upsert Modes** (NEW as of 2026-01-19):
  - **INSERT ONLY** (`mode="insert_only"`): Used by `bulk_update.py` - preserves existing data, only inserts new rows
  - **UPSERT** (`mode="upsert"`): Default behavior - overwrites existing data with new values
  - Both modes available in `DBManager.upsert_dataframe()`, `KRStockCollector.save()`, `IndicatorSaver.save_long()`
- **FinanceDataReader Rate Limits**:
  - External service with strict rate limits
  - Use `apps/ingest-databatcher/core/rate_limiter.py` for thread-safe rate limiting
  - Current config: `rate_limit_per_sec: 5` (adjust in settings.yaml)
  - Excessive requests may result in temporary blocking
- **Market Close Check**: `--force` flag bypasses timing checks for testing/backfills
- **Indicator Index**: Indicators expect DataFrame with DatetimeIndex. Scripts convert date column to index before passing to pipeline
- **Symbol Master Sync**: Run `sync_symbol_master.py` weekly to catch new listings and delistings
- **Parallel vs Sequential**:
  - `bulk_update.py`: Parallel (fast, for initial loads)
  - `daily_update.py --all`: Sequential (simpler and more reliable for daily updates)

## Recent Enhancements

### 2026-02-09: Minervini Trend Template Screening
- ✅ **Screening System**: Pre-computed Minervini Trend Template screening results
- ✅ **Two Tables**: `minervini_screen_results_kr` / `minervini_screen_results_us`
- ✅ **8 Screening Conditions**: MA ordering, SMA200 uptrend, 52-week price levels, RS Rating, Blue Dot (optional)
- ✅ **Batch Scripts**: `kr_minervini_update.py`, `us_minervini_update.py`
- ✅ **Config**: `minervini_kr`, `minervini_us` sections in `apps/ingest-databatcher/config/settings.yaml`
- ✅ **Insert Only**: Passing symbols only, safe re-runs

**New Files**:
- `apps/ingest-databatcher/scripts/migrations/add_minervini_tables.sql`: DB migration
- `apps/ingest-databatcher/indicators/minervini/__init__.py`, `trend_template.py`: Screening logic
- `apps/ingest-databatcher/scripts/kr_minervini_update.py`: KR stock screening batch
- `apps/ingest-databatcher/scripts/us_minervini_update.py`: US stock screening batch
- `guides/미너비니_트렌드_템플릿_가이드.md`: User guide

**Modified Files**:
- `docker/mysql/init/01_schema.sql`: Added minervini screening tables
- `apps/ingest-databatcher/core/bulk_price_loader.py`: Added `load_indicators_wide()` function
- `apps/ingest-databatcher/config/settings.yaml`: Added `minervini_kr`, `minervini_us` sections
- `apps/ingest-databatcher/ops/shell/bulk_all.sh`: Added minervini update steps
- `docs/database_schema.md`: Documented minervini tables
- `guides/DB_데이터_가이드.md`: Added screening tables section
- `CLAUDE.md`: Added minervini commands

### 2026-02-09: Independent Indicator Backfill
- ✅ **Backfill Script**: `backfill_indicators.py` — DB 가격 데이터로부터 지표만 독립 계산/적재
- ✅ **Test DB Init**: `init_test_db.py` — trade_test 데이터베이스 초기화
- ✅ **Backfill Config**: `indicators_backfill` / `indicators_us_backfill` 별도 설정 섹션
- ✅ **Parallel Processing**: ThreadPoolExecutor + tqdm (API 호출 없이 DB 로컬 읽기만)
- ✅ **Dual Mode**: insert_only (기본, 기존 보존) / upsert (덮어쓰기)

**New Files**:
- `apps/ingest-databatcher/scripts/backfill_indicators.py`: 메인 백필 스크립트
- `apps/ingest-databatcher/scripts/init_test_db.py`: 테스트 DB 초기화
- `guides/지표_백필_가이드.md`: 사용자 가이드

**Modified Files**:
- `apps/ingest-databatcher/config/settings.yaml`: `indicators_backfill`, `indicators_us_backfill` 섹션 추가
- `CLAUDE.md`: 백필 명령어 섹션 추가

### 2026-02-08: Sector/Industry Information
- ✅ **KR Sector Classification**: pykrx 대분류 (26개) + FDR KRX-DESC 세분류 (162개) + Industry 수집
- ✅ **US Sector/Industry**: FDR Industry 보존 + yfinance Sector 보완 (증분 처리)
- ✅ **symbol_type 컬럼**: STOCK/ETF 구분 (한국/미국 양쪽)
- ✅ **ETF 섹터 제외**: ETF는 sector 관련 컬럼 항상 NULL
- ✅ **COALESCE 패턴**: US UPDATE 시 기존 sector/industry 값 보존

**New Files**:
- `apps/ingest-databatcher/core/fdr_sector_loader.py`: FDR KRX-DESC 세분류 섹터 fetch
- `apps/ingest-databatcher/scripts/migrations/add_sector_columns.sql`: 마이그레이션 SQL

**Modified Files**:
- `apps/ingest-databatcher/core/pykrx_adapter.py`: `fetch_sector_classifications()` 추가
- `apps/ingest-databatcher/scripts/sync_symbol_master.py`: 섹터 enrichment + upsert 확장
- `apps/ingest-databatcher/scripts/us_sync_symbol_master.py`: Industry 보존 + yfinance + CLI 옵션 추가
- `docker/mysql/init/01_schema.sql`: symbol_master, us_symbol_master 컬럼 추가
- `requirements.txt`: yfinance 추가

### 2026-01-19: Data Collection Optimization
- ✅ **INSERT ONLY Mode**: `bulk_update.py` now preserves existing data (idempotent, safe re-runs)
- ✅ **Smart Daily Updates**: New efficient incremental update strategy
  - Collects 30 days of price data (INSERT ONLY to preserve existing)
  - Loads 250 days from DB for indicator calculation
  - Processes dates in reverse order (newest first)
  - Stops early when complete indicators are detected
- ✅ **Indicator Completeness Check**: `IndicatorChecker` validates all indicators exist for a date
- ✅ **DB Price Loader**: `load_price_data()` utility for efficient DB queries
- ✅ **Simplified Logic**: Explicit, sequential processing instead of complex gap detection

**New Utilities**:
- `apps/ingest-databatcher/core/indicator_checker.py`: Check if all indicators are calculated for a date
- `apps/ingest-databatcher/core/price_loader.py`: Load historical price data from DB

### 2026-01-17: Foundation Features
- ✅ **Symbol Master Management**: Automated sync of all KRX symbols
- ✅ **Bulk Collection**: Parallel processing for historical data collection
- ✅ **Auto Collection Mode**: `--all` flag for daily_update.py to collect all ACTIVE symbols
- ✅ **Market Filtering**: `--market KOSPI/KOSDAQ` options
- ✅ **Rate Limiting**: Thread-safe rate limiter to prevent API blocking

### 2026-02-05: US Stock Support
- ✅ **US Symbol Master**: `us_symbol_master` table for NYSE/NASDAQ/ETF symbols
- ✅ **US Stock Collector**: `USStockCollector` using FinanceDataReader
- ✅ **US Bulk Update**: `us_bulk_update.py` for historical data collection
- ✅ **US Daily Update**: `us_daily_update.py` for incremental updates
- ✅ **US Indicator Pipeline**: `indicators_us` config section
- ✅ **Parameterized Core Modules**: `IndicatorChecker` and `price_loader` now support multiple tables via parameters

**New Files**:
- `apps/ingest-databatcher/collectors/us_stock.py`: US stock data collector
- `apps/ingest-databatcher/core/us_symbol_loader.py`: US symbol loading utilities
- `apps/ingest-databatcher/scripts/us_sync_symbol_master.py`: US symbol master sync
- `apps/ingest-databatcher/scripts/us_bulk_update.py`: US bulk data collection
- `apps/ingest-databatcher/scripts/us_daily_update.py`: US daily updates
- `apps/ingest-databatcher/scripts/probes/fdr_us_stock_probe.py`: FDR US API probe

**Modified Files**:
- `apps/ingest-databatcher/core/indicator_checker.py`: Added `table`, `config_key` parameters
- `apps/ingest-databatcher/core/price_loader.py`: Added `table` parameter
- `apps/ingest-databatcher/config/settings.yaml`: Added `indicators_us` section
- `docker/mysql/init/01_schema.sql`: Added US stock tables

### 2026-02-06: US Index Support
- ✅ **US Index Master**: `us_index_master` table for S&P 500, Dow Jones, NASDAQ Composite
- ✅ **US Index Collector**: `USIndexCollector` using FinanceDataReader (no adj_close)
- ✅ **US Index Bulk Update**: `us_index_bulk_update.py` for historical data collection
- ✅ **US Index Daily Update**: `us_index_daily_update.py` with reverse-order IndicatorChecker pattern
- ✅ **US Index Indicator Pipeline**: `indicators_us_index` config section (SMA 5/20/40)

**New Files**:
- `apps/ingest-databatcher/collectors/us_index.py`: US index data collector
- `apps/ingest-databatcher/core/us_index_symbol_loader.py`: US index symbol loading utilities
- `apps/ingest-databatcher/scripts/us_index_sync_master.py`: US index master sync (3 hardcoded indices)
- `apps/ingest-databatcher/scripts/us_index_bulk_update.py`: US index bulk data collection
- `apps/ingest-databatcher/scripts/us_index_daily_update.py`: US index daily updates
- `apps/ingest-databatcher/scripts/probes/fdr_us_index_probe.py`: FDR US index API probe

**Modified Files**:
- `apps/ingest-databatcher/config/settings.yaml`: Added `indicators_us_index` section
- `docker/mysql/init/01_schema.sql`: Added US index tables (3 tables + 1 view)

### 2026-02-07: US Index Weekly Support
- ✅ **US Index Weekly Tables**: `us_index_prices_weekly`, `us_index_indicators_weekly` (no adj_close)
- ✅ **US Index Weekly Bulk**: `us_index_bulk_update_weekly.py` — daily→weekly aggregation for all indices
- ✅ **US Index Weekly Update**: `us_index_weekly_update.py` — incremental weekly update with reverse-order indicator check
- ✅ **US Index Weekly Config**: `indicators_us_index_weekly` section (SMA 5/20/40)
- ✅ **Weekly View**: `v_us_index_price_weekly_with_ma` (SMA 5/20/40 pivot)

**New Files**:
- `apps/ingest-databatcher/scripts/us_index_bulk_update_weekly.py`: US index weekly bulk data generation
- `apps/ingest-databatcher/scripts/us_index_weekly_update.py`: US index weekly incremental updates
- `apps/ingest-databatcher/scripts/migrations/add_us_index_weekly_tables.sql`: Migration for weekly tables

**Modified Files**:
- `apps/ingest-databatcher/config/settings.yaml`: Added `indicators_us_index_weekly` section
- `docker/mysql/init/01_schema.sql`: Added US index weekly tables (2 tables + 1 view)

### 2026-02-07: IBD RS Rating / RS Line / Blue Dot
- ✅ **IBD RS Rating**: Cross-sectional relative strength percentile (1~99) for KR and US stocks
- ✅ **RS Line**: Stock close / benchmark index close ratio
- ✅ **Blue Dot Signal**: RS Line 52-week high while price is not at 52-week high (0/1)
- ✅ **Bulk Price Loader**: Wide-format all-symbol price loading utility
- ✅ **Config**: `ibd_rs` settings section (weights, benchmarks, strict_12m)

**New Files**:
- `apps/ingest-databatcher/indicators/ibd/__init__.py`: IBD indicators package
- `apps/ingest-databatcher/indicators/ibd/rs_rating.py`: IBD RS Rating calculation
- `apps/ingest-databatcher/indicators/ibd/rs_line.py`: RS Line calculation
- `apps/ingest-databatcher/indicators/ibd/blue_dot.py`: Blue Dot Signal calculation
- `apps/ingest-databatcher/core/bulk_price_loader.py`: All-symbol wide-format price loader
- `apps/ingest-databatcher/scripts/kr_rs_update.py`: KR stock RS indicators batch
- `apps/ingest-databatcher/scripts/us_rs_update.py`: US stock RS indicators batch

**Modified Files**:
- `apps/ingest-databatcher/config/settings.yaml`: Added `ibd_rs` settings section
- `guides/한국주식_일봉_가이드.md`: Added RS indicators section
- `guides/미국주식_일봉_가이드.md`: Added RS indicators section

### Typical Workflow (Production)

**Korean Stocks**:
```bash
# 1. Weekly: Sync symbol master
0 2 * * 0 python apps/ingest-databatcher/scripts/sync_symbol_master.py

# 2. Daily: Update all symbols (optimized)
0 17 * * 1-5 python apps/ingest-databatcher/scripts/daily_update.py --all --force

# 3. Daily: RS indicators (after daily_update, ~17:05)
5 17 * * 1-5 python apps/ingest-databatcher/scripts/kr_rs_update.py --force

# 4. Daily: Minervini screening (after RS update, ~17:10)
10 17 * * 1-5 python apps/ingest-databatcher/scripts/kr_minervini_update.py --days 7 --force
```

**US Stocks**:
```bash
# 1. Weekly: Sync US symbol master
0 2 * * 0 python apps/ingest-databatcher/scripts/us_sync_symbol_master.py

# 2. Daily: Update US symbols (after market close, 16:00 ET + 30min = ~21:30 KST)
0 22 * * 1-5 python apps/ingest-databatcher/scripts/us_daily_update.py --all --with-indicators

# 3. Daily: RS indicators (after us_daily_update, ~07:05 KST)
5 7 * * 1-5 python apps/ingest-databatcher/scripts/us_rs_update.py --force

# 4. Daily: Minervini screening (after RS update, ~07:10 KST)
10 7 * * 1-5 python apps/ingest-databatcher/scripts/us_minervini_update.py --days 7 --force

# 5. Weekly: Update US weekly data (Saturday morning ET / Saturday afternoon KST)
0 10 * * 6 python apps/ingest-databatcher/scripts/us_weekly_update.py --all
```

**US Indices**:
```bash
# 1. Weekly: Sync US index master (rarely changes, but safe to run)
0 2 * * 0 python apps/ingest-databatcher/scripts/us_index_sync_master.py

# 2. Daily: Update US indices (after US market close, ~07:00 KST)
0 7 * * 1-5 python apps/ingest-databatcher/scripts/us_index_daily_update.py --all --force

# 3. Weekly: Update US index weekly data (Saturday morning ET / Saturday afternoon KST)
0 10 * * 6 python apps/ingest-databatcher/scripts/us_index_weekly_update.py --all
```

## Future Enhancements (per 진행상황.md)
- Gap detection and backfill automation (`gap_filler.py`)
- Alert/notification system for specific market conditions
- Retry mechanism for failed symbols in bulk collection
- Integration with Grafana for visualization
- Trading strategy backtesting framework based on PDF training materials
