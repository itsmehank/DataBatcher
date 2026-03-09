# pykrx 전환 리스크 및 보완 계획

**작성일**: 2026-01-27
**목적**: pykrx 전환 시 예상되는 리스크 식별 및 완화 전략 수립

---

## 리스크 매트릭스

| ID | 리스크 | 영향도 | 발생 가능성 | 우선순위 | 완화 전략 | 테스트 결과 |
|----|-------|--------|-----------|----------|----------|-------------|
| R1 | pykrx 스크래핑 중단 | 높음 | 중간 | 🔴 HIGH | Fallback 메커니즘 | - |
| R2 | API 호출 증가 → 성능 저하 | 중간 | 높음 | 🟠 MEDIUM | 캐싱, 배치 처리 | - |
| R3 | 컬럼 매핑 오류 | 높음 | 낮음 | 🟠 MEDIUM | 단위 테스트, 검증 | ✅ 매핑 검증 완료 |
| R4 | 수정주가 계산 차이 | 중간 | 중간 | 🟠 MEDIUM | 비교 검증, 문서화 | ⚠️  추가 검증 필요 |
| R5 | 종목 목록 불일치 | 낮음 | 낮음 | 🟢 VERY LOW | 차집합 분석 | ✅ 100% 일치 |
| R6 | Rate Limiting 차단 | 중간 | 낮음 | 🟢 LOW | 속도 제한, 모니터링 | - |
| R7 | 데이터 누락 | 높음 | 낮음 | 🟠 MEDIUM | 검증 로직, 알림 | ✅ 6/6 성공 |
| R8 | 휴장일 처리 차이 | 낮음 | 낮음 | 🟢 LOW | 테스트, 문서화 | - |

**영향도**: 발생 시 시스템에 미치는 영향 (높음/중간/낮음)
**발생 가능성**: 리스크가 실제 발생할 확률 (높음/중간/낮음)

---

## 🔴 HIGH Priority 리스크

### R1: pykrx 스크래핑 중단

**설명**:
- pykrx는 KRX 웹사이트를 스크래핑하는 라이브러리
- KRX 웹사이트 구조 변경 시 pykrx 동작 중단 가능
- pykrx 라이브러리 업데이트 전까지 데이터 수집 불가

**영향**:
- ❌ 전체 데이터 수집 파이프라인 중단
- ❌ 일일 업데이트 실패
- ❌ 서비스 다운타임 발생

**발생 시나리오**:
1. KRX 웹사이트 리뉴얼
2. HTML 구조 변경
3. API 엔드포인트 변경
4. 봇 차단 정책 강화

**완화 전략**:

#### 1. Fallback 메커니즘 구현
```python
# collectors/collector_factory.py (신규)

def get_price_collector(engine, config, symbol: str):
    """
    Primary collector 실패 시 fallback으로 전환
    """
    primary = config['collectors']['primary']
    fallback_enabled = config['collectors'].get('fallback', True)

    try:
        if primary == 'pykrx':
            collector = KRStockCollectorPykrx(engine)
            # 간단한 health check
            _ = collector.fetch(symbol, start='2024-01-01', end='2024-01-31')
            return collector
    except Exception as e:
        logger.warning(f"pykrx collector failed: {e}")
        if fallback_enabled:
            logger.info("Falling back to FDR collector")
            return KRStockCollector(engine)  # FDR
        else:
            raise
```

#### 2. 모니터링 및 알림
- **수집 성공률 추적**: 일일 성공률이 90% 이하로 떨어지면 알림
- **에러 로그 모니터링**: pykrx 관련 에러 급증 시 알림
- **Health Check**: 매 실행 전 샘플 종목으로 사전 검증

#### 3. pykrx 업데이트 추적
- **GitHub Watch**: pykrx repository를 watch하여 이슈/커밋 알림 받기
- **버전 고정**: `requirements.txt`에서 pykrx 버전 고정
  ```
  pykrx==1.0.51  # 검증된 안정 버전
  ```
- **주기적 업데이트 검토**: 월 1회 pykrx 최신 버전 테스트

#### 4. 다중 데이터 소스 전략 (장기)
- pykrx, FDR 외에 추가 소스 검토 (한국투자증권 API, KIS API 등)
- 데이터 소스를 플러그인 방식으로 관리

**완료 기준**:
- [x] Fallback 메커니즘 구현 및 테스트
- [ ] 모니터링 대시보드 구축
- [ ] pykrx GitHub watch 설정
- [ ] 주간 Health Check 자동화

---

## 🟠 MEDIUM Priority 리스크

### R2: API 호출 증가 → 성능 저하

**설명**:
- pykrx는 FDR 대비 약 2배 많은 API 호출 필요
- Symbol Sync: 4 + N회 (FDR: 1회)
- 종목 3,000개 기준: 6,004회 호출 (FDR: 3,001회)

**영향**:
- ⏱️ Symbol Sync 시간 증가: 2분 → 5-10분
- ⏱️ Bulk Update 시간 증가: 15분 → 30분
- ⚠️ KRX 서버 부하 → Rate Limiting 위험

**완화 전략**:

#### 1. 종목명 캐싱 (DB)
```sql
-- symbol_master 테이블에 last_updated 컬럼 추가
ALTER TABLE symbol_master ADD COLUMN name_updated_at DATETIME;

-- 캐시 유효 기간: 24시간
SELECT symbol, name FROM symbol_master
WHERE name_updated_at > NOW() - INTERVAL 24 HOUR;
```

```python
def fetch_krx_listing_with_cache(engine, date_str: str = None):
    """
    종목명을 DB 캐시에서 먼저 조회, 없으면 pykrx API 호출
    """
    # 1. DB에서 최근 24시간 이내 캐시 조회
    cached = load_cached_symbols(engine)

    # 2. 캐시 미스 종목만 API 호출
    missing = get_market_ticker_list() - cached.keys()

    for ticker in missing:
        name = stock.get_market_ticker_name(ticker)
        # DB 캐시 갱신
        update_symbol_cache(engine, ticker, name)

    # ...
```

**효과**: API 호출 3,000회 → 100-200회 (신규/변경 종목만)

#### 2. 시가총액 배치 조회
```python
# 기존 (비효율)
for ticker in tickers:
    marcap = stock.get_market_cap(date_str, ticker)  # N회 호출

# 개선 (효율)
marcap_df = stock.get_market_cap(date_str, market='ALL')  # 1회 호출
# 전체 종목 시가총액을 한 번에 조회 후 merge
```

**효과**: API 호출 3,000회 → 1회

#### 3. Rate Limiting 재조정
```yaml
# config/settings.yaml
runtime:
  rate_limit_per_sec: 10  # FDR: 5 → pykrx: 10
  rate_limit_burst: 20
```

**근거**: pykrx는 공식 API가 아니므로 신중하게 증가

#### 4. 병렬 처리 (신중하게)
```python
# 주의: Rate Limiting 고려 필수
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=4) as executor:
    futures = [executor.submit(fetch_symbol, s) for s in symbols]
    # ...
```

**완료 기준**:
- [ ] DB 캐싱 구현 및 테스트
- [ ] 배치 조회 적용
- [ ] Sync 시간 10분 이내 달성

---

### R3: 컬럼 매핑 오류

**✅ 실제 테스트 결과 (2026-01-27)**:
- pykrx 실제 컬럼: `시가, 고가, 저가, 종가, 거래량, 등락률`
- FDR 컬럼: `Open, High, Low, Close, Volume, Change`
- **매핑 1:1 대응 가능 확인**
- **리스크 발생 가능성: 낮음 → 매우 낮음으로 하향**

**설명**:
- pykrx 컬럼(한글) → 프로젝트 컬럼(영문) 매핑 필수
- 매핑 누락 시 런타임 에러 또는 데이터 손실

**영향**:
- ❌ KeyError 발생 (컬럼 미존재)
- ❌ 데이터 손실 (누락된 컬럼)
- ❌ 지표 계산 실패

**발생 시나리오**:
1. pykrx 업데이트로 새 컬럼 추가
2. 매핑 테이블 미갱신
3. 런타임 에러 발생

**완화 전략**:

#### 1. 명시적 검증 로직
```python
def normalize_price_columns(df: pd.DataFrame) -> pd.DataFrame:
    """컬럼 매핑 + 검증"""
    df = df.copy()

    # 미매핑 컬럼 확인
    unmapped = set(df.columns) - set(PRICE_COLUMN_MAPPING.keys())
    if unmapped:
        logger.warning(f"Unmapped columns detected: {unmapped}")
        logger.warning("Consider updating PRICE_COLUMN_MAPPING")

    # 매핑 실행
    df = df.rename(columns=PRICE_COLUMN_MAPPING)

    # 필수 컬럼 존재 확인
    required = ['open', 'high', 'low', 'close', 'volume']
    missing = set(required) - set(df.columns)
    if missing:
        raise ValueError(f"Required columns missing after mapping: {missing}")

    return df
```

#### 2. 단위 테스트
```python
# tests/test_pykrx_adapter.py

def test_column_mapping():
    """모든 pykrx 컬럼이 매핑되는지 확인"""
    sample_df = pd.DataFrame({
        '시가': [100],
        '고가': [110],
        '저가': [90],
        '종가': [105],
        '거래량': [1000],
        '거래대금': [100000],
        '등락률': [5.0],
    })

    result = normalize_price_columns(sample_df)

    # 모든 컬럼이 영문으로 변환되었는지 확인
    assert '시가' not in result.columns
    assert 'open' in result.columns
    assert 'high' in result.columns
    # ...
```

#### 3. 버전 고정
```
# requirements.txt
pykrx==1.0.51  # 검증된 버전, 업데이트 전 충분한 테스트 필요
```

**완료 기준**:
- [x] 검증 로직 구현
- [ ] 단위 테스트 100% 커버리지
- [ ] 버전 고정

---

### R4: 수정주가 계산 차이

**설명**:
- FDR과 pykrx의 수정주가 계산 알고리즘이 다를 수 있음
- 특히 액면분할, 무상증자 등 이벤트 처리 방식 차이 가능

**영향**:
- 📊 기술적 지표 값 변동 (SMA, EMA 등)
- 📊 백테스팅 결과 차이
- 📊 과거 데이터와 불연속성

**완화 전략**:

#### 1. 비교 검증
```python
# scripts/tests/compare_adjusted_prices.py

def compare_adjusted_prices(symbol: str, start: str, end: str):
    """FDR vs pykrx 수정주가 비교"""
    # FDR
    fdr_df = fdr.DataReader(symbol, start, end)

    # pykrx (adjusted=True)
    pykrx_df = stock.get_market_ohlcv(
        to_pykrx_date(start),
        to_pykrx_date(end),
        symbol,
        adjusted=True
    )

    # 종가 비교
    diff = abs(fdr_df['Close'] - pykrx_df['종가']) / fdr_df['Close']
    max_diff = diff.max()

    print(f"Max difference: {max_diff:.4%}")

    if max_diff > 0.01:  # 1% 이상 차이
        print("⚠️  Significant difference detected")
        # 상세 분석...
```

**샘플 종목**: 삼성전자, SK하이닉스, 현대차, NAVER, 카카오

#### 2. 허용 오차 정의
- **0.1% 이하**: 정상 (반올림 오차)
- **0.1% ~ 1%**: 주의 (원인 분석 필요)
- **1% 이상**: 심각 (알고리즘 차이, 조사 필수)

#### 3. 문서화
- 차이 발견 시 `docs/adjusted_price_differences.md`에 기록
- 원인, 허용 여부, 대응 방안 명시

#### 4. 사용자 옵션 제공
```yaml
# config/settings.yaml
collectors:
  pykrx:
    use_adjusted: true  # 수정주가 사용 여부
```

**완료 기준**:
- [ ] 대표 종목 5개 비교 완료
- [ ] 차이 1% 이하 확인
- [ ] 차이 문서화

---

### R7: 데이터 누락

**✅ 실제 테스트 결과 (2026-01-27)**:
- 테스트 종목: 6개
- 성공률: **6/6 (100%)**
- 데이터 행 수: 모두 20행으로 일치
- **발생 가능성: 낮음 유지 (테스트 기간 짧음)**

**설명**:
- pykrx API 실패, 네트워크 오류, 종목 코드 오류 등으로 데이터 누락 가능

**영향**:
- 📉 불완전한 데이터셋
- 📉 지표 계산 오류
- 📉 분석 결과 왜곡

**완화 전략**:

#### 1. 검증 로직
```python
def validate_price_data(df: pd.DataFrame, symbol: str, start: date, end: date) -> bool:
    """
    수집된 데이터의 완결성 검증

    Returns:
        True: 정상, False: 이상 감지
    """
    if df is None or df.empty:
        logger.error(f"{symbol}: No data returned")
        return False

    # 기대 거래일 수 계산 (휴장일 제외)
    expected_days = get_trading_days(start, end)

    # 실제 데이터 행 수
    actual_days = len(df)

    # 허용 오차: 5일 (휴장일 처리 차이 감안)
    if abs(expected_days - actual_days) > 5:
        logger.warning(
            f"{symbol}: Expected {expected_days} days, got {actual_days}"
        )
        return False

    # 필수 컬럼 결측치 확인
    required = ['open', 'high', 'low', 'close', 'volume']
    na_counts = df[required].isna().sum()

    if na_counts.any():
        logger.warning(f"{symbol}: Missing values detected: {na_counts}")
        return False

    return True
```

#### 2. 재시도 메커니즘
```python
def fetch_with_retry(symbol: str, start, end, max_retries=3):
    """실패 시 재시도"""
    for attempt in range(max_retries):
        try:
            df = stock.get_market_ohlcv(...)
            if validate_price_data(df, symbol, start, end):
                return df
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed: {e}")
            time.sleep(2 ** attempt)  # Exponential backoff

    logger.error(f"{symbol}: Failed after {max_retries} attempts")
    return None
```

#### 3. 알림
- 일일 수집 완료 후 요약 리포트 생성
- 실패 종목 > 10개 시 이메일/Slack 알림

**완료 기준**:
- [ ] 검증 로직 구현
- [ ] 재시도 메커니즘 적용
- [ ] 알림 시스템 구축

---

## 🟢 LOW Priority 리스크

### R5: 종목 목록 불일치

**✅ 실제 테스트 결과 (2026-01-27)**:
- FDR: 2,888개 (KOSPI + KOSDAQ + KONEX)
- pykrx: 2,888개 (KOSPI 951 + KOSDAQ 1,825 + KONEX 112)
- **차이: 0개 (100% 일치)**
- **우선순위: LOW → VERY LOW로 하향 조정**

**설명** (이론적 가능성):
- FDR과 pykrx에서 제공하는 종목 목록이 약간 다를 수 있음
- 상장폐지 종목 처리 시점 차이
- ETF, 우선주 포함 여부 차이

**영향**:
- 일부 종목 누락 또는 추가 (실제 테스트에서는 미발생)
- 수집 대상 종목 수 변동

**완화 전략**:

#### 1. 차집합 분석 자동화
```python
def analyze_symbol_diff(fdr_symbols: set, pykrx_symbols: set):
    """FDR vs pykrx 종목 차이 분석"""
    common = fdr_symbols & pykrx_symbols
    fdr_only = fdr_symbols - pykrx_symbols
    pykrx_only = pykrx_symbols - fdr_symbols

    report = f"""
    Symbol Listing Comparison
    =========================
    Common: {len(common)}
    FDR only: {len(fdr_only)}
    pykrx only: {len(pykrx_only)}

    FDR only samples: {list(fdr_only)[:10]}
    pykrx only samples: {list(pykrx_only)[:10]}
    """

    # 로그 저장
    with open('logs/symbol_diff_report.txt', 'w') as f:
        f.write(report)

    return report
```

#### 2. Manual Review
- 차이 종목 리스트를 주기적으로 검토
- ETF, 우선주, 상장폐지 종목 확인
- 포함/제외 기준 명확화

**완료 기준**:
- [ ] 차집합 분석 스크립트 작성
- [ ] 초기 리뷰 완료

---

### R6: Rate Limiting 차단

**설명**:
- 과도한 요청 시 KRX 서버에서 IP 차단 가능

**영향**:
- 일시적 데이터 수집 불가 (수 시간)

**완화 전략**:
1. Rate Limiter 설정 (10 req/sec)
2. Exponential backoff
3. IP 로테이션 (필요 시)

---

### R8: 휴장일 처리 차이

**설명**:
- FDR과 pykrx의 휴장일 데이터 누락 방식이 다를 수 있음

**영향**:
- 날짜별 데이터 행 수 차이
- 지표 계산 시 인덱스 불일치

**완화 전략**:
1. 거래일 캘린더 사용 (`pandas_market_calendars`)
2. 휴장일 데이터는 수집하지 않음 (양쪽 동일)
3. 테스트로 검증

---

## 모니터링 체크리스트

### 일일 모니터링
- [ ] 수집 성공률 (목표: 95% 이상)
- [ ] 평균 수집 시간 (목표: Sync 10분, Bulk 30분)
- [ ] 에러 로그 건수 (목표: 10건 이하)

### 주간 모니터링
- [ ] pykrx GitHub 이슈 확인
- [ ] 실패 종목 패턴 분석
- [ ] 데이터 품질 샘플링 (무작위 10개 종목)

### 월간 모니터링
- [ ] pykrx 버전 업데이트 검토
- [ ] 수정주가 비교 (대표 종목 5개)
- [ ] 성능 최적화 검토

---

## 비상 대응 계획 (Contingency Plan)

### Scenario 1: pykrx 완전 중단
**대응**:
1. 즉시 FDR로 Fallback 전환
2. pykrx GitHub에 이슈 등록
3. 커뮤니티 상황 파악
4. 필요 시 자체 스크래핑 로직 개발 또는 유료 API 전환 검토

**예상 복구 시간**: 24시간 (Fallback 자동 전환)

---

### Scenario 2: Rate Limiting 차단
**대응**:
1. Rate Limit 설정 절반으로 감소 (10 → 5 req/sec)
2. 수집 간격 증가 (배치 크기 감소)
3. 24시간 대기 후 재시도

**예상 복구 시간**: 24-48시간

---

### Scenario 3: 데이터 품질 이슈
**대응**:
1. 해당 종목 FDR로 수집
2. 원인 분석 (로그, 웹사이트 확인)
3. pykrx 이슈 등록
4. 임시 블랙리스트 추가

**예상 복구 시간**: 즉시 (개별 종목 fallback)

---

## 실제 테스트 결과 요약 (2026-01-27)

### ✅ 테스트 검증 완료

**테스트 범위**:
- 기간: 2025-12-28 ~ 2026-01-27 (1개월)
- 가격 데이터: 6개 종목 (KOSPI 5개, KOSDAQ 1개)
- 종목 목록: 전체 KRX (2,888개)

**검증 결과**:
1. **R3 (컬럼 매핑)**:
   - ✅ pykrx 컬럼 구조 확인: `시가, 고가, 저가, 종가, 거래량, 등락률`
   - ✅ 1:1 매핑 가능
   - **리스크 완화됨**

2. **R5 (종목 목록 불일치)**:
   - ✅ FDR vs pykrx: 2,888개 완벽 일치 (차이 0개)
   - **우선순위: LOW → VERY LOW**
   - **리스크 거의 제거됨**

3. **R7 (데이터 누락)**:
   - ✅ 6/6 종목 성공 (100%)
   - ✅ 데이터 행 수 일치
   - **발생 가능성 낮음 재확인**

**주요 발견**:
- ⚠️  거래대금은 OHLCV API에 미포함 (별도 API 필요)
- ⚠️  수정주가 (adjusted 옵션) 추가 검증 필요
- ✅ 전반적으로 매우 높은 호환성 확인

---

## 요약

**HIGH 리스크**: 1개 (pykrx 스크래핑 중단)
- **핵심 완화**: Fallback 메커니즘 필수

**MEDIUM 리스크**: 4개
- 캐싱, 검증, 테스트로 대응
- **✅ R3 (컬럼 매핑): 테스트 검증 완료**

**LOW 리스크**: 2개
- 모니터링 및 문서화로 관리

**VERY LOW 리스크**: 1개 (NEW)
- **✅ R5 (종목 목록 불일치): 테스트에서 100% 일치 확인**

**전체 리스크 수용 가능 여부**: ✅ YES (테스트 결과로 확신 강화)
- 모든 HIGH/MEDIUM 리스크에 대한 완화 전략 존재
- Fallback 메커니즘으로 서비스 연속성 보장
- 단계적 전환으로 리스크 최소화
- **실제 테스트에서 높은 호환성 검증 완료**

---

**작성자**: Claude Code
**버전**: 2.0 (실제 테스트 결과 반영)
**최종 수정**: 2026-01-27
**테스트 완료**: 2026-01-27