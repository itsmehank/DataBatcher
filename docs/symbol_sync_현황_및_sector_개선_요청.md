# DataBatcher Symbol Master 동기화 현황 및 Sector 정보 수집 개선 요청

## 1. 프로젝트 개요

DataBatcher는 한국(KRX), 미국(NYSE/NASDAQ), 크립토(Binance) 시장의 주가 데이터를 수집하고 기술적 지표를 계산하여 MySQL에 저장하는 시스템입니다.

이 문서는 **종목 마스터(Symbol Master) 동기화** 로직을 정리한 것으로, 각 종목의 **산업(Sector) 정보를 함께 수집**하기 위한 개선 방안을 논의하기 위해 작성되었습니다.

---

## 2. 한국 주식 (KRX) Symbol 동기화

### 2.1 사용 패키지

| 패키지 | 버전/용도 | 비고 |
|--------|-----------|------|
| **pykrx** | KRX 종목 목록, 종목명, 시가총액 조회 | 2026-01-27에 FDR에서 전환 |
| **pandas** | 데이터 변환/정제 | |
| **sqlalchemy** | DB 연결 및 SQL 실행 | |

### 2.2 데이터 수집 흐름

```
scripts/sync_symbol_master.py
  └─ core/pykrx_adapter.py :: fetch_krx_listing()
```

**Step 1: 주식 종목 수집** (`fetch_krx_listing()`)
```python
from pykrx import stock

# 시장별 종목코드 목록 조회
for market in ['KOSPI', 'KOSDAQ', 'KONEX']:
    tickers = stock.get_market_ticker_list(date_str, market=market)

    # 종목별 종목명 조회 (개별 API 호출, ~2,900회)
    for ticker in tickers:
        name = stock.get_market_ticker_name(ticker)

# 시가총액 배치 조회
marcap_df = stock.get_market_cap(date_str, market='ALL')
# 컬럼: 시가총액 → Marcap으로 rename 후 merge
```

**Step 2: ETF 종목 수집** (`fetch_etf_listing()`)
```python
tickers = stock.get_etf_ticker_list(date_str)
for t in tickers:
    name = stock.get_etf_ticker_name(t)
    # Market = 'ETF'
```

**Step 3: 병합 및 충돌 처리**
- 동일 symbol이 주식과 ETF 양쪽에 있으면 → **주식 우선**, ETF 스킵
- 충돌 내역은 `logs/sync_symbol_master_etf_conflicts.log`에 기록

**Step 4: DB 비교 및 분류**
- NEW: FDR에 있고 DB에 없음 → INSERT (status=ACTIVE)
- UPDATE: 양쪽 모두 존재 → UPDATE (name, market 갱신)
- DELISTED: DB에 있고 FDR에 없음 → status='DELISTED'로 변경
- ETF delist guard: ETF 대량 삭제 방지 안전장치 (500개 미만 또는 80% 미만이면 ETF delist 차단)

### 2.3 수집되는 데이터 (중간 DataFrame)

| 컬럼명 | 타입 | 출처 | 설명 |
|--------|------|------|------|
| symbol (Code) | str | `get_market_ticker_list()` | 종목코드 (e.g., '005930') |
| Name | str | `get_market_ticker_name()` | 종목명 (e.g., '삼성전자') |
| Market | str | 수집 시 직접 지정 | KOSPI / KOSDAQ / KONEX / ETF |
| Marcap | int | `get_market_cap()` | 시가총액 (원 단위) |

### 2.4 저장 테이블: `symbol_master`

```sql
CREATE TABLE IF NOT EXISTS symbol_master (
  symbol        VARCHAR(32) PRIMARY KEY,          -- e.g., '005930'
  market        VARCHAR(16) NOT NULL,             -- KOSPI / KOSDAQ / KONEX / ETF
  name          VARCHAR(128) NULL,                -- 종목명
  status        VARCHAR(16) NOT NULL,             -- ACTIVE / DELISTED / IPO_PENDING
  first_date    DATE NULL,                        -- (현재 미사용)
  last_date     DATE NULL,                        -- (현재 미사용)
  updated_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**실제 INSERT/UPDATE되는 컬럼**: `symbol`, `market`, `name`, `status`, `updated_at`

> **참고**: `first_date`, `last_date`는 스키마에만 존재하고 sync 스크립트에서는 사용하지 않음. `Marcap`(시가총액)도 pykrx에서 수집은 하지만 DB에 저장하는 컬럼이 없음.

### 2.5 현재 sector 정보 상태

- **pykrx**: 기본 API에서 sector/industry 정보를 직접 제공하지 않음
- **symbol_master 테이블**: sector/industry 컬럼이 **없음**
- 현재 수집 가능한 메타데이터: symbol, name, market, marcap(미저장)

---

## 3. 미국 주식 (US) Symbol 동기화

### 3.1 사용 패키지

| 패키지 | 버전/용도 | 비고 |
|--------|-----------|------|
| **FinanceDataReader (fdr)** | NYSE/NASDAQ/ETF 종목 목록 조회 | `pip install finance-datareader` |
| **pandas** | 데이터 변환/정제 | |
| **sqlalchemy** | DB 연결 및 SQL 실행 | |

### 3.2 데이터 수집 흐름

```
scripts/us_sync_symbol_master.py
  └─ FinanceDataReader.StockListing()
```

**Step 1: 시장별 종목 목록 가져오기**
```python
import FinanceDataReader as fdr

# 각 시장별 배치 조회 (한번에 전체 목록 반환)
df_nyse   = fdr.StockListing('NYSE')      # NYSE 종목
df_nasdaq = fdr.StockListing('NASDAQ')     # NASDAQ 종목
df_etf    = fdr.StockListing('ETF/US')     # US ETF
```

**Step 2: 컬럼 정규화**
```python
# FDR이 반환하는 컬럼명이 일정하지 않으므로 정규화
if 'Symbol' in df.columns:
    df.rename(columns={'Symbol': 'symbol'})
if 'name' in df.columns:
    df.rename(columns={'name': 'Name'})

# Market 컬럼 직접 지정
df['Market'] = market   # 'NYSE', 'NASDAQ', 또는 'ETF'
```

**Step 3: 결합 및 중복 제거**
```python
fdr_df = pd.concat([df_nyse, df_nasdaq, df_etf], ignore_index=True)
fdr_df = fdr_df.drop_duplicates(subset=['symbol'], keep='first')
```

**Step 4: DB 비교 및 분류** (한국과 동일한 패턴)
- NEW → INSERT (status=ACTIVE)
- UPDATE → UPDATE (name, market 갱신)
- DELISTED → status='DELISTED'

### 3.3 수집되는 데이터 (중간 DataFrame)

| 컬럼명 | 타입 | 출처 | 설명 |
|--------|------|------|------|
| symbol | str | `StockListing()` 결과의 Symbol 컬럼 | 티커 (e.g., 'AAPL') |
| Name | str | `StockListing()` 결과의 Name 컬럼 | 회사명 (e.g., 'Apple Inc.') |
| Market | str | 수집 시 직접 지정 | NYSE / NASDAQ / ETF |

> **참고**: `fdr.StockListing()`은 시장에 따라 추가 컬럼(Industry, Sector 등)을 반환할 수 있으나, 현재 스크립트에서는 `['symbol', 'Name', 'Market']` 3개 컬럼만 선택하여 사용함.

### 3.4 저장 테이블: `us_symbol_master`

```sql
CREATE TABLE IF NOT EXISTS us_symbol_master (
  symbol        VARCHAR(32) PRIMARY KEY,          -- e.g., 'AAPL', 'MSFT'
  market        VARCHAR(16) NOT NULL,             -- NYSE / NASDAQ / ETF
  name          VARCHAR(256) NULL,                -- Company name
  status        VARCHAR(16) NOT NULL,             -- ACTIVE / DELISTED
  sector        VARCHAR(128) NULL,                -- 섹터 정보 (현재 미사용)
  industry      VARCHAR(128) NULL,                -- 산업 정보 (현재 미사용)
  etl_loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**실제 INSERT/UPDATE되는 컬럼**: `symbol`, `market`, `name`, `status`, `etl_loaded_at`, `updated_at`

### 3.5 현재 sector 정보 상태

- **us_symbol_master 테이블**: `sector`, `industry` 컬럼이 **이미 존재**하지만 NULL 상태
- **FinanceDataReader**: `StockListing('NYSE')` 등의 반환값에 `Industry` 컬럼이 포함될 수 있으나, 현재 스크립트에서 이 컬럼을 사용하지 않고 있음
- 현재 `fetch_us_listing()` 함수에서 `df[['symbol', 'Name', 'Market']]`으로 3개 컬럼만 반환하여 나머지 정보가 버려지고 있음

---

## 4. 한국 vs 미국 비교 요약

| 항목 | 한국 (KRX) | 미국 (US) |
|------|-----------|-----------|
| **스크립트** | `scripts/sync_symbol_master.py` | `scripts/us_sync_symbol_master.py` |
| **데이터 소스** | pykrx | FinanceDataReader (fdr) |
| **데이터 소스 API** | `stock.get_market_ticker_list()` + `stock.get_market_ticker_name()` (개별 호출) | `fdr.StockListing('NYSE')` 등 (배치 호출) |
| **시장 구분** | KOSPI, KOSDAQ, KONEX, ETF | NYSE, NASDAQ, ETF |
| **저장 테이블** | `symbol_master` | `us_symbol_master` |
| **sector 컬럼** | 없음 | 있음 (NULL 상태) |
| **industry 컬럼** | 없음 | 있음 (NULL 상태) |
| **시가총액 수집** | 수집하지만 저장 안함 | 수집 안함 |
| **종목 수** | ~2,900개 | ~7,000-8,000개 |
| **소요 시간** | 1-2분 (개별 API 호출로 느림) | 30-60초 (배치 호출로 빠름) |
| **실행 주기** | 주 1회 권장 | 주 1회 권장 |

---

## 5. 개선 요청 사항: Sector 정보 수집 추가

### 5.1 목표

각 종목의 **산업 분류(sector/industry)** 정보를 symbol master 동기화 시 함께 수집하여 DB에 저장하고자 합니다.

### 5.2 현재 상태 요약

| 시장 | DB 컬럼 존재 여부 | 데이터 소스에서 제공 여부 | 현재 수집 여부 |
|------|-------------------|--------------------------|---------------|
| **한국 (KRX)** | sector/industry 컬럼 **없음** | pykrx 기본 API에서는 미제공 | X |
| **미국 (US)** | sector/industry 컬럼 **있음** (NULL) | FDR StockListing에서 일부 제공 가능 | X (3개 컬럼만 사용 중) |

### 5.3 구체적으로 답변을 원하는 질문들

1. **한국 주식 sector 정보**:
   - pykrx 또는 다른 무료 라이브러리에서 KRX 종목의 업종(sector) 정보를 가져올 수 있는 방법이 있는가?
   - KRX에서 제공하는 업종 분류 체계(GICS, WICS, KRX 업종분류 등) 중 어떤 것을 사용하는 것이 적절한가?
   - `symbol_master` 테이블에 어떤 컬럼을 추가해야 하는가? (sector, industry, sub_industry 등)

2. **미국 주식 sector 정보**:
   - `fdr.StockListing('NYSE')` 반환값에 실제로 어떤 sector/industry 관련 컬럼이 포함되는가?
   - FDR에서 제공하지 않는다면, 대안 패키지(yfinance 등)로 sector 정보를 수집하는 방법은?
   - `us_symbol_master`의 기존 `sector`/`industry` 컬럼에 바로 저장하면 되는가, 아니면 스키마 변경이 필요한가?

3. **공통 설계 질문**:
   - Sector 정보는 symbol master sync 시 함께 수집하는 것이 적절한가, 아니면 별도 스크립트로 분리해야 하는가?
   - 한국/미국 모두 GICS 분류 체계로 통일하는 것이 분석에 유리한가?
   - ETF의 경우 sector 분류를 어떻게 처리해야 하는가?

---

## 6. 참고: 관련 파일 목록

```
DataBatcher/
├── scripts/
│   ├── sync_symbol_master.py          # 한국 종목 마스터 동기화
│   └── us_sync_symbol_master.py       # 미국 종목 마스터 동기화
├── core/
│   ├── pykrx_adapter.py               # pykrx 래퍼 (fetch_krx_listing 함수 포함)
│   ├── symbol_loader.py               # 한국 종목 로더 (DB에서 종목 목록 조회)
│   ├── us_symbol_loader.py            # 미국 종목 로더
│   ├── db_manager.py                  # DB 연결 및 upsert 유틸리티
│   └── config_loader.py               # 설정 파일 로드
├── config/
│   └── settings.yaml                  # 전체 설정 (DB 접속, 지표 파이프라인 등)
└── docker/
    └── mysql/init/01_schema.sql       # 전체 DB 스키마 정의
```