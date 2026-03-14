# FDR → pykrx 전환 전략

**작성일**: 2026-01-27
**목적**: FinanceDataReader에서 pykrx로의 안전하고 단계적인 전환 계획 수립

---

## 전환 배경

### 현재 상황 (FinanceDataReader)
- **데이터 소스**: 주로 Yahoo Finance 기반
- **커버리지**: 글로벌 주식, 환율, 암호화폐 등 광범위
- **제약사항**:
  - Rate Limiting 엄격 (5 req/sec 설정)
  - 일부 종목에서 데이터 누락 (93% 성공률)
  - 데이터 출처 불명확 (신뢰성 검증 어려움)
  - Adj Close 컬럼 불안정

### 전환 목표 (pykrx)
- **데이터 소스**: KRX 공식 웹사이트 스크래핑
- **장점**:
  - 한국 시장 전문 라이브러리
  - 공식 출처 (신뢰성 향상)
  - 더 상세한 국내 데이터 (재무제표, 공매도 등)
  - `adjusted` 옵션으로 수정주가 지원
- **기대 효과**:
  - 데이터 신뢰성 향상
  - 성공률 개선 (상장폐지 종목 등 정확한 필터링)
  - 추가 데이터 활용 가능 (재무, 공매도 등)

---

## 핵심 기술 차이 분석

### 1. 가격 데이터 수집 API

#### FinanceDataReader
```python
import FinanceDataReader as fdr
df = fdr.DataReader(symbol, start="2024-01-01", end="2024-12-31")

# 반환 컬럼 (영문)
# Index: Date (DatetimeIndex)
# Columns: Open, High, Low, Close, Volume, Change, [Adj Close]
```

#### pykrx
```python
from pykrx import stock
df = stock.get_market_ohlcv("20240101", "20241231", symbol)

# 반환 컬럼 (한글) - ✅ 실제 테스트 확인됨
# Index: 날짜 (DatetimeIndex)
# Columns: 시가, 고가, 저가, 종가, 거래량, 등락률
# 주의: 거래대금은 별도 API (get_market_trading_value_by_date)로 조회
```

#### 주요 차이점

| 항목 | FDR | pykrx | 전환 영향 |
|-----|-----|-------|---------|
| **날짜 포맷** | `YYYY-MM-DD` (str) | `YYYYMMDD` (str) | 포맷 변환 필요 |
| **컬럼명** | 영문 (Open, High, ...) | 한글 (시가, 고가, ...) | **매핑 레이어 필수** |
| **인덱스** | DatetimeIndex (Date) | DatetimeIndex (날짜) | ✅ 동일 (테스트 확인) |
| **Change** | 제공 (Change) | 제공 (등락률) | 둘 다 미사용 → 매핑 불필요 |
| **Adj Close** | 불안정 (종목별 상이) | `adjusted=True` 옵션 | 옵션 명시 필요 |
| **거래대금** | 미제공 | ❌ OHLCV에 미포함 | 별도 API로 조회 필요 |

---

### 2. 종목 목록 조회 API

#### FinanceDataReader
```python
import FinanceDataReader as fdr
df = fdr.StockListing('KRX')

# 반환 컬럼
# Columns: Code, Name, Market, Marcap, Stocks, ...
```

#### pykrx
```python
from pykrx import stock

# 시장별 조회 필요
kospi = stock.get_market_ticker_list("20260127", market="KOSPI")
kosdaq = stock.get_market_ticker_list("20260127", market="KOSDAQ")
konex = stock.get_market_ticker_list("20260127", market="KONEX")

# 종목명 조회 (각 종목마다 개별 호출)
for ticker in kospi:
    name = stock.get_market_ticker_name(ticker)
    # ...

# 시가총액 조회 (날짜별 전체 종목)
df_marcap = stock.get_market_cap("20260127", market="ALL")
# Columns: 시가총액, 거래량, 거래대금, ...
```

#### 주요 차이점

| 항목 | FDR | pykrx | 전환 영향 |
|-----|-----|-------|---------|
| **조회 방식** | 단일 호출 | 시장별 개별 호출 | **루프 로직 필요** |
| **종목명** | 목록에 포함 | 개별 조회 필요 | API 호출 증가 |
| **시가총액** | 목록에 포함 | `get_market_cap()` 별도 호출 | API 호출 증가 |
| **날짜 의존성** | 없음 | 날짜 필수 (YYYYMMDD) | 현재 날짜 전달 필요 |
| **컬럼명** | 영문 (Code, Name, ...) | 한글 (종목명, 시가총액, ...) | 매핑 필요 |

---

## 전환 시 필수 구현 사항

### 1. 컬럼명 매핑 레이어 (핵심)

**목적**: 한글 컬럼명을 영문으로 정규화하여 기존 로직 호환성 유지

**구현 방안**:

```python
# core/pykrx_adapter.py (신규 파일)

# ✅ 실제 테스트 결과 반영 (2026-01-27)
PRICE_COLUMN_MAPPING = {
    '시가': 'open',
    '고가': 'high',
    '저가': 'low',
    '종가': 'close',
    '거래량': 'volume',
    '등락률': 'change_rate',  # FDR의 Change에 대응 (현재 미사용)
}

# 주의: 거래대금은 OHLCV에 포함되지 않음
# 필요 시 stock.get_market_trading_value_by_date()로 별도 조회

def normalize_price_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    pykrx 가격 데이터의 한글 컬럼을 영문으로 변환

    Args:
        df: pykrx.stock.get_market_ohlcv() 반환 DataFrame

    Returns:
        정규화된 DataFrame (open, high, low, close, volume, ...)
    """
    df = df.copy()
    df = df.rename(columns=PRICE_COLUMN_MAPPING)

    # 인덱스 이름 정규화
    df.index.name = 'date'

    return df
```

**적용 위치**: `collectors/kr_stock.py` → `fetch()` 메서드

---

### 2. 날짜 포맷 변환 유틸리티

**구현**:

```python
# core/pykrx_adapter.py

from datetime import datetime, date

def to_pykrx_date(dt: date | str) -> str:
    """
    Python date 또는 'YYYY-MM-DD' 문자열을 pykrx 형식('YYYYMMDD')으로 변환

    Examples:
        >>> to_pykrx_date(date(2024, 1, 1))
        '20240101'
        >>> to_pykrx_date('2024-01-01')
        '20240101'
    """
    if isinstance(dt, str):
        dt = datetime.strptime(dt, '%Y-%m-%d').date()
    return dt.strftime('%Y%m%d')

def from_pykrx_date(dt_str: str) -> date:
    """
    pykrx 날짜 형식('YYYYMMDD')을 Python date로 변환
    """
    return datetime.strptime(dt_str, '%Y%m%d').date()
```

---

### 3. 종목 목록 조회 어댑터

**문제**: pykrx는 시장별 개별 조회 + 종목명/시가총액 별도 조회 필요

**해결**:

```python
# core/pykrx_adapter.py

def fetch_krx_listing(date_str: str = None) -> pd.DataFrame:
    """
    pykrx를 사용하여 FDR StockListing('KRX')과 동일한 구조로 종목 목록 조회

    Args:
        date_str: 조회 날짜 (YYYYMMDD), None이면 오늘 날짜

    Returns:
        DataFrame with columns: Code, Name, Market, Marcap, ...
        (FDR 호환 컬럼명)
    """
    from pykrx import stock
    from datetime import datetime

    if date_str is None:
        date_str = datetime.now().strftime('%Y%m%d')

    results = []

    # 각 시장별로 조회
    for market in ['KOSPI', 'KOSDAQ', 'KONEX']:
        tickers = stock.get_market_ticker_list(date_str, market=market)

        for ticker in tickers:
            # 종목명 조회
            name = stock.get_market_ticker_name(ticker)

            results.append({
                'Code': ticker,
                'Name': name,
                'Market': market,
            })

    df = pd.DataFrame(results)

    # 시가총액 추가 (한 번에 조회)
    try:
        marcap_df = stock.get_market_cap(date_str, market='ALL')
        # marcap_df.columns = ['시가총액', '거래량', '거래대금', ...]
        marcap_df = marcap_df.rename(columns={'시가총액': 'Marcap'})

        # ticker를 기준으로 merge
        df = df.merge(
            marcap_df[['Marcap']],
            left_on='Code',
            right_index=True,
            how='left'
        )
    except Exception as e:
        # 시가총액 조회 실패 시 NA 처리
        df['Marcap'] = pd.NA

    return df
```

**주의사항**:
- API 호출 횟수 증가 (종목당 1회 + 시가총액 1회)
- Rate Limiting 고려 필요
- 캐싱 전략 검토

---

### 4. 수정주가 처리

**FDR**: `Adj Close` 컬럼 불안정 (종목별 상이)

**pykrx**: `adjusted` 파라미터로 명시적 제어

**구현**:

```python
# collectors/kr_stock.py (수정 예정)

def fetch(self, symbol: str, start, end, adjusted: bool = True) -> pd.DataFrame:
    """
    Fetch price data from pykrx for a KRX symbol.

    Args:
        symbol: 종목코드
        start: 시작일
        end: 종료일
        adjusted: True면 수정주가, False면 비수정주가

    Returns:
        DataFrame with columns: symbol, date, open, high, low, close,
                               adj_close, volume, market, source
    """
    from pykrx import stock
    from core.pykrx_adapter import to_pykrx_date, normalize_price_columns

    start_str = to_pykrx_date(start)
    end_str = to_pykrx_date(end)

    # pykrx 데이터 수집
    df = stock.get_market_ohlcv(start_str, end_str, symbol, adjusted=adjusted)

    if df is None or df.empty:
        return df

    # 컬럼명 정규화 (한글 → 영문)
    df = normalize_price_columns(df)

    # FDR 호환을 위해 adj_close 컬럼 추가
    if adjusted:
        df['adj_close'] = df['close']  # 이미 수정주가이므로 동일
    else:
        df['adj_close'] = pd.NA  # 비수정주가면 NA

    # 기존 로직과 동일하게 메타데이터 추가
    df = df.reset_index()
    df['symbol'] = symbol
    df['market'] = 'XKRX'
    df['source'] = 'pykrx'

    # 날짜 컬럼을 date 타입으로 변환
    df['date'] = pd.to_datetime(df['date']).dt.date

    # 최종 컬럼 순서 (FDR 호환)
    expected = [
        'symbol', 'date', 'open', 'high', 'low', 'close',
        'adj_close', 'volume', 'market', 'source'
    ]

    # 추가 컬럼 (pykrx 전용) 제거 또는 보존
    # 옵션 1: 제거 (FDR 완전 호환)
    df = df[expected]

    # 옵션 2: 보존 (추후 활용)
    # for col in ['trading_value', 'change_rate']:
    #     if col not in df.columns:
    #         df[col] = pd.NA

    return df
```

---

## 전환 단계별 로드맵

### Phase 0: 준비 단계 (현재)
- [x] FDR 사용 현황 분석 완료
- [x] pykrx 특성 조사 완료
- [x] 전환 전략 수립 완료
- [ ] pykrx 테스트 코드 실행 및 검증
- [ ] 전환 계획서 최종 승인

### Phase 1: 기반 구축 (1-2일)
**목표**: pykrx 어댑터 레이어 구축 및 단위 테스트

**작업**:
1. `core/pykrx_adapter.py` 신규 생성
   - `normalize_price_columns()` 구현
   - `to_pykrx_date()` / `from_pykrx_date()` 구현
   - `fetch_krx_listing()` 구현
2. 단위 테스트 작성 (`tests/test_pykrx_adapter.py`)
   - 컬럼 매핑 검증
   - 날짜 변환 검증
   - 종목 목록 조회 검증
3. 샘플 종목(삼성전자 등)으로 통합 테스트

**완료 기준**:
- 모든 단위 테스트 통과
- 샘플 종목에서 FDR과 pykrx 결과 일치 확인

---

### Phase 2: Collector 전환 (2-3일)
**목표**: `collectors/kr_stock.py` pykrx 버전 구현

**작업**:
1. `collectors/kr_stock_pykrx.py` 신규 생성 (기존 파일 보존)
   - `KRStockCollectorPykrx` 클래스 구현
   - `fetch()` 메서드에 pykrx 로직 적용
   - `save()` 메서드는 기존 코드 재사용
2. 비교 테스트 스크립트 작성
   - FDR vs pykrx 데이터 비교
   - 10개 샘플 종목으로 검증
3. 실패 케이스 로깅 및 분석

**완료 기준**:
- 샘플 종목에서 95% 이상 일치
- 실패 케이스 원인 파악 및 문서화

---

### Phase 3: Symbol Master 전환 (1-2일)
**목표**: `scripts/sync_symbol_master.py` pykrx 버전 구현

**작업**:
1. `scripts/sync_symbol_master_pykrx.py` 신규 생성
   - `fetch_krx_listing()` 어댑터 사용
   - 기존 비교/분류 로직 재사용
2. Dry-run 모드 구현 (DB 변경 없이 시뮬레이션)
3. 실제 DB 동기화 테스트 (개발 환경)

**완료 기준**:
- FDR vs pykrx 종목 목록 차이 1% 이하 (✅ 실제 테스트: 0%)
- 차이 종목 분석 및 정당성 확인

---

### Phase 4: 통합 테스트 (3-5일)
**목표**: 전체 파이프라인 pykrx 버전 검증

**작업**:
1. `bulk_update_pykrx.py` 작성
   - pykrx collector 사용
   - 소수 종목(상위 10개)으로 전체 파이프라인 테스트
2. `daily_update_pykrx.py` 작성
   - 일일 업데이트 시나리오 테스트
3. 데이터 무결성 검증
   - `stock_prices` 테이블 FDR vs pykrx 비교
   - `stock_indicators` 계산 결과 동일성 확인

**완료 기준**:
- 전체 파이프라인 정상 동작
- 지표 계산 결과 일치 (오차 0.1% 이하)

---

### Phase 5: 단계적 전환 (1주)
**목표**: 프로덕션 환경에서 안전하게 전환

**전략**: Dual-run (FDR + pykrx 병행)

**작업**:
1. Config 설정 추가 (`config/settings.yaml`)
   ```yaml
   collectors:
     primary: "pykrx"    # "fdr" 또는 "pykrx"
     fallback: true      # primary 실패 시 fallback 사용 여부
   ```
2. Collector 팩토리 패턴 적용
   ```python
   def get_collector(engine, config):
       primary = config['collectors']['primary']
       if primary == 'pykrx':
           return KRStockCollectorPykrx(engine)
       else:
           return KRStockCollector(engine)  # FDR
   ```
3. 단계별 전환:
   - **Week 1**: pykrx 10% 종목 (상위 100개)
   - **Week 2**: pykrx 50% 종목
   - **Week 3**: pykrx 100% 종목
   - **Week 4**: 모니터링 및 안정화
4. 모니터링:
   - 수집 성공률 추적
   - 실패 종목 로깅
   - 데이터 품질 검증

**완료 기준**:
- pykrx 성공률 95% 이상
- 데이터 품질 이슈 없음
- 성능 저하 없음

---

### Phase 6: 정리 및 최적화 (2-3일)
**목표**: FDR 코드 제거 및 최적화

**작업**:
1. FDR 관련 코드 제거
   - `collectors/kr_stock.py` 삭제 또는 deprecated
   - `requirements.txt`에서 `finance-datareader` 제거
2. 테스트 스크립트 정리
   - FDR 관련 테스트 제거
   - pykrx 테스트만 유지
3. 문서 업데이트
   - `CLAUDE.md` 수정 (FDR → pykrx)
   - README 업데이트
4. 성능 최적화
   - Rate limiting 재조정
   - 캐싱 전략 검토

**완료 기준**:
- FDR 의존성 완전 제거
- 문서 최신화
- 성능 유지 또는 개선

---

## 리스크 및 완화 전략

### 리스크 1: pykrx API 호출 증가
**현상**: 종목 목록 조회 시 종목당 1회 + 시가총액 1회 호출

**영향**:
- Sync 시간 증가 (2-3분 → 10-15분 예상)
- KRX 서버 부하 → Rate limiting 위험

**완화**:
1. **캐싱**: 종목명, 시가총액을 메모리 캐싱 (24시간 유효)
2. **배치 처리**: `get_market_cap()` 한 번에 전체 조회 후 merge
3. **점진적 업데이트**: 신규/변경 종목만 조회

---

### 리스크 2: 컬럼명 매핑 누락
**현상**: 새로운 컬럼 추가 시 매핑 테이블 누락

**영향**:
- 런타임 에러
- 데이터 손실

**완화**:
1. **명시적 검증**: `normalize_price_columns()`에 미매핑 컬럼 경고
2. **테스트 커버리지**: 모든 컬럼 매핑 단위 테스트
3. **버전 관리**: pykrx 버전 고정 (`requirements.txt`)

---

### 리스크 3: 수정주가 계산 방식 차이
**현상**: FDR과 pykrx의 수정주가 알고리즘 차이 가능

**영향**:
- 기술적 지표 값 변동
- 백테스팅 결과 차이

**완화**:
1. **비교 검증**: 대표 종목 5개로 수정주가 비교
2. **문서화**: 차이 발견 시 원인 및 허용 범위 문서화
3. **옵션 제공**: 사용자가 FDR/pykrx 선택 가능하도록 config

---

### 리스크 4: pykrx 스크래핑 안정성
**현상**: KRX 웹사이트 구조 변경 시 pykrx 동작 중단

**영향**:
- 데이터 수집 전면 중단
- 서비스 다운타임

**완화**:
1. **Fallback 메커니즘**: pykrx 실패 시 FDR로 자동 전환 (Phase 5에서 구현)
2. **모니터링**: 수집 성공률 실시간 추적
3. **업데이트 추적**: pykrx GitHub Issues 구독
4. **버전 고정**: 안정 버전 사용, 업데이트 전 충분한 테스트

---

### 리스크 5: 종목 목록 차이
**✅ 실제 테스트 결과 (2026-01-27)**:
- FDR: 2,888개 / pykrx: 2,888개
- **차이: 0개 (100% 일치)**
- **리스크 수준: LOW → VERY LOW로 하향 조정**

**현상** (이론적 가능성): FDR과 pykrx에서 제공하는 종목 목록이 다를 수 있음

**영향**:
- 일부 종목 누락 또는 추가 (실제 테스트에서는 미발생)
- 데이터 불일치

**완화** (예방적 조치):
1. **차집합 분석**: Sync 시 FDR vs pykrx 종목 차이 리포트 생성
2. **Manual Review**: 차이 종목 수동 검토 후 포함/제외 결정
3. **로깅**: 차이 종목을 `logs/symbol_diff.log`에 기록

---

## 성능 및 비용 고려사항

### API 호출 횟수 비교

**FDR (현재)**:
- Symbol Sync: 1회 (전체 KRX)
- Price Data: 종목당 1회
- **Total**: 1 + N (N = 종목 수)

**pykrx (전환 후)**:
- Symbol Sync:
  - 시장별 목록: 3회 (KOSPI, KOSDAQ, KONEX)
  - 종목명: N회
  - 시가총액: 1회
  - **Total**: 4 + N
- Price Data: 종목당 1회
- **Total**: (4 + N) + N = 4 + 2N

**결론**:
- pykrx가 약 2배 많은 API 호출
- 종목 수 3,000개 기준: FDR 3,001회 → pykrx 6,004회
- **Sync 시간 증가 예상**: 2분 → 5-10분

**최적화 방안**:
1. 종목명 캐싱 (DB 또는 Redis)
2. 변경 종목만 업데이트 (delta sync)
3. Parallel requests (신중하게, Rate Limiting 고려)

---

### Rate Limiting

**FDR**:
- 현재 설정: 5 req/sec
- 근거: Yahoo Finance 제약

**pykrx**:
- 공식 제한 없음 (확인 필요)
- KRX 웹사이트 스크래핑 → 과도한 요청 시 차단 위험
- **권장 설정**: 10 req/sec (초기), 모니터링 후 조정

**구현**:
```yaml
# config/settings.yaml
runtime:
  rate_limit_per_sec: 10  # pykrx용으로 증가
  rate_limit_burst: 20    # 버스트 허용
```

---

## 실제 테스트 결과 요약 (2026-01-27)

### ✅ Phase 0 완료: 테스트 검증 성공

**테스트 환경**:
- 기간: 2025-12-28 ~ 2026-01-27 (1개월)
- 종목: 6개 (삼성전자, SK하이닉스, 현대차, 카카오, NAVER, 에코프로비엠)

**결과**:
1. **가격 데이터 수집**: ✅ 6/6 성공 (100%)
2. **종목 목록 일치**: ✅ 2,888/2,888 (100% 일치)
3. **인덱스 타입**: ✅ 둘 다 DatetimeIndex (동일)
4. **데이터 행 수**: ✅ 모두 20행으로 일치

**확인된 컬럼 구조**:
- FDR: `Open, High, Low, Close, Volume, Change`
- pykrx: `시가, 고가, 저가, 종가, 거래량, 등락률`
- 매핑: 1:1 대응 가능

**주요 발견**:
- ✅ 종목 목록 100% 일치 → 리스크 5 하향 조정
- ✅ 데이터 품질 우수 → 전환 가능성 높음
- ⚠️  거래대금은 OHLCV에 미포함 (별도 API 필요)
- ⚠️  Adj Close는 FDR에서도 불안정 (종목/기간 의존)

**결론**: **전환 가능 (높은 호환성)**

---

## 다음 단계

1. ~~**pykrx 설치 및 테스트 실행**~~ ✅ 완료 (2026-01-27)

2. ~~**테스트 결과 검토**~~ ✅ 완료
   - ✅ `scripts/tests/pykrx_comparison_report.md` 생성됨
   - ✅ 컬럼 매핑 정확성 검증 완료
   - ✅ 데이터 일치도 100% 확인

3. **Phase 1 착수 승인** ⬅️ 현재 단계
   - 전환 계획서 최종 검토 (이 문서)
   - 리스크 문서 업데이트 (pykrx_migration_risks.md)
   - 리스크 수용 여부 결정
   - 일정 및 리소스 할당

---

**참고 자료**:
- [pykrx GitHub](https://github.com/sharebook-kr/pykrx)
- [pykrx 사용법 가이드](https://wikidocs.net/228554)
- [FDR vs pykrx 비교](https://unfinishedgod.netlify.app/2023/07/03/python-pykrk-part-1/)

**작성자**: Claude Code
**버전**: 2.0 (실제 테스트 결과 반영)
**최종 수정**: 2026-01-27
**테스트 완료**: 2026-01-27