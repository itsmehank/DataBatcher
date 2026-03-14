# FinanceDataReader 사용 현황 분석

**분석 일자**: 2026-01-27
**분석 대상**: DataBatcher 프로젝트 전체
**목적**: pykrx 전환을 위한 현황 파악

---

## 요약

DataBatcher 프로젝트는 현재 **FinanceDataReader (FDR)** 라이브러리를 사용하여:
1. 개별 종목의 가격 데이터 수집 (`fdr.DataReader`)
2. KRX 전체 종목 목록 조회 (`fdr.StockListing`)

총 **5개 파일**에서 FDR을 사용 중이며, 이 중 **2개**가 핵심 프로덕션 코드입니다.

---

## 사용 파일 목록

### ✅ 핵심 프로덕션 코드 (2개)

#### 1. `collectors/kr_stock.py`

**역할**: 개별 종목의 가격 데이터 수집 및 DB 저장

**사용 FDR 함수**:
```python
fdr.DataReader(symbol, start=start, end=end)
```

**수집 데이터**:
- **종류**: 개별 종목 일별 가격 데이터 (OHLCV)
- **입력 파라미터**:
  - `symbol`: 종목코드 (예: "005930")
  - `start`: 시작일 (datetime or str)
  - `end`: 종료일 (datetime or str)
- **반환 DataFrame 컬럼** (FDR 원본):
  ```
  Index: Date (DatetimeIndex)
  Columns: Open, High, Low, Close, Volume, Change, [Adj Close]
  ```
  - `Adj Close`는 종목에 따라 존재하지 않을 수 있음
  - `Change`는 수집 후 제거됨

**후속 처리**:
1. 컬럼명을 소문자로 변환
2. "adj close" → "adj_close"로 rename
3. "change" 컬럼 삭제
4. `symbol`, `market` (XKRX), `source` (FDR) 컬럼 추가
5. `date` 컬럼을 `datetime.date` 타입으로 변환
6. 최종 컬럼: `symbol, date, open, high, low, close, adj_close, volume, market, source`
7. `stock_prices` 테이블에 UPSERT (mode 파라미터로 insert_only 가능)

**데이터 활용**:
- 기술적 지표 계산의 입력 데이터
- `indicators/pipeline.py`에서 SMA, EMA 등의 지표 계산에 사용
- 백테스팅 및 분석의 기초 데이터

---

#### 2. `scripts/sync_symbol_master.py`

**역할**: KRX 전체 종목 목록 동기화

**사용 FDR 함수**:
```python
fdr.StockListing('KRX')
```

**수집 데이터**:
- **종류**: KRX 전체 상장 종목 목록 (KOSPI, KOSDAQ, KONEX)
- **입력 파라미터**: `'KRX'` (고정값)
- **반환 DataFrame 컬럼** (FDR 원본):
  ```
  Columns: Code, Name, Market, Marcap, Stocks, ...
  ```
  - `Code`: 종목코드 (str)
  - `Name`: 종목명 (str, 한글)
  - `Market`: 시장 구분 (KOSPI/KOSDAQ/KONEX)
  - `Marcap`: 시가총액 (int, 억원 단위)
  - `Stocks`: 상장주식수 (int)

**후속 처리**:
1. `Code` → `symbol`로 rename
2. DB의 기존 종목과 비교:
   - **신규 종목**: DB에 INSERT (status=ACTIVE)
   - **기존 종목**: 종목명/시장 정보 UPDATE
   - **상장폐지 종목**: status를 DELISTED로 변경
3. `symbol_master` 테이블 갱신

**데이터 활용**:
- `bulk_update.py`, `daily_update.py`에서 수집 대상 종목 결정
- `--all` 옵션 사용 시 ACTIVE 상태의 종목만 수집
- `--market KOSPI/KOSDAQ` 필터링
- `--top N` 시가총액 상위 N개 종목 선택

**실행 주기**: 주 1회 권장 (신규 상장/상장폐지 감지)

---

### ⚙️ 테스트/검증 스크립트 (3개)

#### 3. `scripts/test_failed_symbols.py`

**역할**: bulk_update.py 실패 종목 진단

**사용 FDR 함수**:
```python
fdr.DataReader(symbol, start="2024-01-01", end="2024-12-31")
```

**목적**:
- 실패한 종목 코드가 FDR에서 데이터를 가져올 수 있는지 검증
- 종목코드 패턴 분석 (예: V0, Y0 등 특수 접미사)
- 성공 종목과 비교

**데이터 활용**: 진단 목적 (프로덕션 비사용)

---

#### 4. `scripts/verify_krx_symbols.py`

**역할**: 실패 종목이 현재 KRX 목록에 있는지 확인

**사용 FDR 함수**:
```python
fdr.StockListing('KRX')
```

**목적**:
- 실패 종목이 상장폐지되었는지 확인
- 종목코드 패턴 분석
- symbol_master 동기화 필요 여부 판단

**데이터 활용**: 진단 목적 (프로덕션 비사용)

---

#### 5. `scripts/probes/fdr_stock_probe.py`

**역할**: FDR 데이터 탐색 및 디버깅 도구

**사용 FDR 함수**:
```python
fdr.DataReader(symbol, start, end)
```

**목적**:
- 특정 종목의 FDR 데이터 구조 확인
- 컬럼, 결측치, 날짜 범위 등 탐색
- 개발/디버깅 도구

**데이터 활용**: 개발 도구 (프로덕션 비사용)

---

## 데이터 흐름 요약

### 주간 동기화 (Weekly)
```
fdr.StockListing('KRX')
  ↓
compare with DB
  ↓
symbol_master 테이블 갱신
  ↓
(신규/변경/상장폐지 종목 반영)
```

### 일일 데이터 수집 (Daily)
```
symbol_master에서 ACTIVE 종목 로드
  ↓
각 종목별로:
  fdr.DataReader(symbol, start, end)
    ↓
  컬럼 정규화 및 변환
    ↓
  stock_prices 테이블 저장
    ↓
  indicators/pipeline.py 실행
    ↓
  stock_indicators 테이블 저장
```

---

## FDR 데이터 특성

### 1. 가격 데이터 (`fdr.DataReader`)

**장점**:
- 간단한 API (symbol, start, end만 필요)
- 수정주가(Adj Close) 제공 (종목에 따라)
- 글로벌 시장 지원 (미국, 한국, 일본 등)

**단점**:
- 데이터 출처가 불명확 (주로 Yahoo Finance 추정)
- Rate Limiting 엄격 (현재 5 req/sec 설정)
- 일부 종목(상장폐지, SPAC 등)에서 None/empty 반환
- Adj Close 컬럼 불안정 (있을 수도, 없을 수도)

**데이터 신뢰성**:
- 대부분의 메이저 종목에서 안정적
- 특수 종목(V0, Y0 접미사 등)에서 실패 가능
- 93% 성공률 확인됨 (bulk_update.py 테스트 기준)

---

### 2. 종목 목록 (`fdr.StockListing`)

**장점**:
- KRX 전체 종목 한 번에 조회
- 시장 구분(KOSPI/KOSDAQ/KONEX) 제공
- 시가총액, 상장주식수 정보 포함

**단점**:
- 실시간 데이터 아님 (1일 지연 가능)
- 데이터 출처 불명확
- API 안정성 의존

---

## 전환 시 고려사항

### 1. 컬럼명 차이
- FDR: `Open, High, Low, Close, Volume, Change, Adj Close`
- pykrx 예상: 다른 컬럼명 (검증 필요)

### 2. 인덱스 구조
- FDR: DatetimeIndex (자동 설정)
- pykrx 예상: 확인 필요

### 3. 데이터 타입
- FDR: datetime.date로 변환 필요
- pykrx: 확인 필요

### 4. 결측치 처리
- FDR: 휴장일 데이터 없음
- pykrx: 확인 필요

### 5. Rate Limiting
- FDR: 엄격 (5 req/sec)
- pykrx: KRX 공식 API → 제한 확인 필요

### 6. Adj Close (수정주가)
- FDR: 불안정 (종목별 상이)
- pykrx: 지원 여부 확인 필요

---

## 영향을 받는 스크립트

### 직접 수정 필요
1. `collectors/kr_stock.py` - **핵심**
2. `scripts/sync_symbol_master.py` - **핵심**

### 간접 영향
3. `scripts/bulk_update.py` - collector 사용
4. `scripts/daily_update.py` - collector 사용
5. `scripts/test_failed_symbols.py` - 테스트 스크립트
6. `scripts/verify_krx_symbols.py` - 검증 스크립트
7. `scripts/probes/fdr_stock_probe.py` - 프로브 스크립트

---

## 다음 단계

1. **pykrx 테스트 코드 작성**:
   - `fdr.DataReader()` 대체 → `pykrx.stock` 함수 탐색
   - `fdr.StockListing()` 대체 → `pykrx.stock` 종목 목록 함수 탐색
   - 컬럼명, 인덱스 구조, 데이터 타입 비교

2. **전환 전략 수립**:
   - 단순 치환 가능 여부 판단
   - 어댑터 레이어 필요성 검토
   - 단계별 마이그레이션 계획

3. **리스크 분석**:
   - 데이터 누락 가능성
   - 성능/속도 차이
   - 휴장일 처리 방식

---

**작성자**: Claude Code
**버전**: 1.0
**최종 수정**: 2026-01-27