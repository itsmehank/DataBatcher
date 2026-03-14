# IBD RS Rating, RS Line, Blue Dot 지표 추가 계획

## Context

미국 주식(ETF 포함)과 한국 주식(ETF 포함) 일봉 데이터에 IBD/O'Neil 스타일의 3가지 지표를 추가한다:
1. **IBD RS Rating** (1~99): 전 종목 대비 상대강도 백분위 순위
2. **RS Line**: 개별 종목 vs 벤치마크 지수의 상대강도 비율
3. **Blue Dot Signal**: RS Line이 52주 신고가인데 주가는 아직 신고가 아닌 시그널

**핵심 설계 이슈**: 기존 지표(SMA, EMA)는 **개별 종목 단위** 계산이지만, IBD RS Rating은 **전 종목 횡단면(cross-sectional)** 계산이 필요하여 기존 `BaseIndicator` → `IndicatorPipeline` 패턴에 맞지 않음. RS Line도 지수 데이터를 별도로 참조해야 함.

→ **별도 배치 스크립트**로 구현하되, 저장은 기존 indicator 테이블 인프라를 재사용한다.

---

## 확인된 설계 결정사항

- **RS Rating 랭킹 범위**: 시장별 독립 랭킹 (한국 종목끼리만, 미국 종목끼리만 백분위 순위)
- **ETF 벤치마크**: 동일 벤치마크 적용 (한국 ETF → KOSPI, 미국 ETF → S&P 500)
- **KOSDAQ 벤치마크**: KOSPI(1001) 통일 (O'Neil 방식: 전체 시장 대비 강도)

---

## 아키텍처 결정

| 항목 | 결정 | 이유 |
|------|------|------|
| 계산 방식 | 별도 배치 스크립트 | 횡단면 계산은 per-symbol 파이프라인에 안 맞음 |
| 저장 테이블 | 기존 `stock_indicators` / `us_stock_indicators` | 동일 long-form 스키마 재사용 |
| RS Line 저장값 | **원본 비율** (stock_close / index_close) | base 정규화는 조회 시 처리, Blue Dot 판단에 원본 비율이면 충분 |
| 실행 순서 | RS Line → IBD RS Rating → Blue Dot | RS Rating은 독립, Blue Dot은 RS Line 의존 |
| strict_12m 옵션 | config에서 설정 가능 (기본 True) | IBD 원칙 준수하되 유연성 확보 |

---

## 구현 계획

### 1단계: 계산 모듈 생성 (KR/US 공용)

**파일: `indicators/ibd/rs_rating.py`** — IBD RS Rating 계산 로직
```
- calculate_ibd_rs_rating(prices_wide_df, strict_12m=True) → DataFrame
  - prices_wide_df: columns=symbols, index=dates, values=close
  - 3/6/9/12개월 수익률 계산 (shift 63/126/189/252)
  - 가중합: 0.4*3m + 0.2*6m + 0.2*9m + 0.2*12m
  - 횡단면 rank(axis=1, pct=True) * 100 → clip(1,99).round()
  - 반환: 동일 shape DataFrame (값=1~99 RS Rating)
```

**파일: `indicators/ibd/rs_line.py`** — RS Line 계산 로직
```
- calculate_rs_line(stock_close_series, index_close_series) → Series
  - 원본 비율: stock_close / index_close
  - 날짜 정렬 후 반환
```

**파일: `indicators/ibd/blue_dot.py`** — Blue Dot 시그널 계산 로직
```
- calculate_blue_dot(stock_close_series, rs_line_series, lookback=252) → Series
  - rs_new_high = rs_line >= rs_line.rolling(lookback).max()
  - price_new_high = stock_close >= stock_close.rolling(lookback).max()
  - blue_dot = rs_new_high & ~price_new_high → int (0/1)
```

**파일: `indicators/ibd/__init__.py`** — 패키지 초기화

### 2단계: 데이터 로더 유틸리티

**파일: `core/bulk_price_loader.py`** — 전 종목 가격 일괄 로드
```
- load_all_prices_wide(engine, start_date, end_date, table, market=None) → DataFrame
  - SELECT symbol, date, close FROM {table} WHERE date BETWEEN ...
  - pivot: index=date, columns=symbol, values=close
  - KR: table="stock_prices"
  - US: table="us_stock_prices"
  - market 필터 옵션 (KOSPI/KOSDAQ/ETF 또는 NYSE/NASDAQ/ETF)

- load_index_close(engine, index_symbol, start_date, end_date, table) → Series
  - 벤치마크 지수 close 가격 로드
  - KR: table="kr_index_prices", symbol="1001" (KOSPI)
  - US: table="us_index_prices", symbol="US500" (S&P 500)
```

### 3단계: 한국 주식 배치 스크립트

**파일: `scripts/kr_rs_update.py`**
```
용도: 한국 주식(ETF 포함) IBD RS Rating + RS Line + Blue Dot 일괄 계산/저장

인자:
  --end YYYY-MM-DD    기준 종료일 (기본: 마지막 영업일)
  --days N            계산 대상 일수 (기본: 30, 최근 N 거래일)
  --market            KOSPI/KOSDAQ/ETF/ALL (기본: ALL)
  --force             마감 체크 무시
  --strict-12m        12개월 미만 종목 제외 (기본: True)

처리 흐름:
  1. symbol_master에서 ACTIVE 종목 목록 로드
  2. stock_prices에서 전 종목 close 가격 로드 (wide format, ~252+days)
  3. kr_index_prices에서 KOSPI(1001) close 로드
  4. IBD RS Rating 계산 (전 종목 횡단면)
  5. RS Line 계산 (각 종목 vs KOSPI)
  6. Blue Dot 계산 (RS Line + 주가 기반)
  7. 최근 N일에 대해 long-form 변환 → stock_indicators에 INSERT ONLY 저장
```

### 4단계: 미국 주식 배치 스크립트

**파일: `scripts/us_rs_update.py`**
```
용도: 미국 주식(ETF 포함) IBD RS Rating + RS Line + Blue Dot 일괄 계산/저장

인자:
  --end YYYY-MM-DD    기준 종료일 (기본: US Eastern 어제)
  --days N            계산 대상 일수 (기본: 30)
  --market            NYSE/NASDAQ/ETF/ALL (기본: ALL)
  --force             마감 체크 무시
  --with-indicators   (호환용, 기본 True)
  --strict-12m        12개월 미만 종목 제외 (기본: True)

처리 흐름:
  1. us_symbol_master에서 ACTIVE 종목 목록 로드
  2. us_stock_prices에서 전 종목 close 가격 로드 (wide format)
  3. us_index_prices에서 S&P 500(US500) close 로드
  4~7. 한국 주식과 동일 로직
  → us_stock_indicators에 INSERT ONLY 저장
```

### 5단계: 설정 추가

**파일: `config/settings.yaml`** — 아래 섹션 추가
```yaml
# IBD RS / RS Line / Blue Dot 설정 (KR/US 공용)
ibd_rs:
  strict_12m: true          # 12개월 미만 종목 제외 (IBD 원칙)
  rs_rating_weights:        # 기간별 가중치
    3m: 0.4
    6m: 0.2
    9m: 0.2
    12m: 0.2
  blue_dot_lookback: 252    # Blue Dot 52주 lookback
  benchmarks:
    kr: "1001"              # KOSPI 지수 심볼
    us: "US500"             # S&P 500 지수 심볼
```

### 6단계: 저장 시 params_hash 정의

기존 `core/params.py`의 `params_hash()` 함수를 그대로 사용:

| 지표 | indicator 컬럼값 | params_hash 계산 입력 |
|------|------------------|---------------------|
| IBD RS Rating | `ibd_rs_rating` | `params_hash("ibd_rs_rating", {"strict_12m": true})` |
| RS Line | `rs_line` | `params_hash("rs_line", {"benchmark": "1001"})` (KR) / `{"benchmark": "US500"}` (US) |
| Blue Dot | `blue_dot` | `params_hash("blue_dot", {"lookback": 252, "benchmark": "1001"})` (KR) |

---

## 파일 변경 요약

### 신규 파일 (7개)
| 파일 | 역할 |
|------|------|
| `indicators/ibd/__init__.py` | 패키지 초기화 |
| `indicators/ibd/rs_rating.py` | IBD RS Rating 계산 로직 |
| `indicators/ibd/rs_line.py` | RS Line 계산 로직 |
| `indicators/ibd/blue_dot.py` | Blue Dot 시그널 계산 로직 |
| `core/bulk_price_loader.py` | 전 종목 가격 일괄 로드 유틸리티 |
| `scripts/kr_rs_update.py` | 한국 주식 RS 지표 배치 스크립트 |
| `scripts/us_rs_update.py` | 미국 주식 RS 지표 배치 스크립트 |

### 수정 파일 (1개)
| 파일 | 변경 내용 |
|------|----------|
| `config/settings.yaml` | `ibd_rs` 설정 섹션 추가 |

### 기존 파일 변경 없음
- `indicators/pipeline.py` — 변경 불필요 (별도 스크립트에서 직접 저장)
- `core/indicator_checker.py` — 변경 불필요 (params_hash 기반으로 자동 호환)
- `savers/indicator_saver.py` — 그대로 재사용
- `core/db_manager.py` — 그대로 재사용
- DB 스키마 — 변경 불필요 (기존 indicator 테이블의 long-form 구조 재사용)

---

## 실행 순서 (Production)

```bash
# 한국 주식: daily_update.py 실행 후에 RS 지표 계산
python scripts/daily_update.py --all --force
python scripts/kr_rs_update.py --force

# 미국 주식: us_daily_update.py 실행 후에 RS 지표 계산
python scripts/us_daily_update.py --all --with-indicators
python scripts/us_rs_update.py --force
```

Cron 예시:
```bash
# KR: 평일 17:05 (daily_update 완료 후)
5 17 * * 1-5 python scripts/kr_rs_update.py --force

# US: 평일 07:05 KST (us_daily_update 완료 후)
5 7 * * 1-5 python scripts/us_rs_update.py --force
```

---

## 검증 방법

1. **단위 테스트**: 소수 종목(삼성전자 005930, AAPL)으로 계산 결과 확인
```bash
python scripts/kr_rs_update.py --market KOSPI --days 5 --force
python scripts/us_rs_update.py --market NASDAQ --days 5 --force
```

2. **DB 검증**:
```sql
-- RS Rating 확인 (1~99 범위)
SELECT symbol, date, indicator, value
FROM stock_indicators
WHERE indicator = 'ibd_rs_rating'
ORDER BY date DESC, value DESC
LIMIT 20;

-- RS Line 확인
SELECT symbol, date, indicator, value
FROM stock_indicators
WHERE indicator = 'rs_line' AND symbol = '005930'
ORDER BY date DESC LIMIT 10;

-- Blue Dot 시그널 확인 (value=1인 행)
SELECT symbol, date, indicator, value
FROM stock_indicators
WHERE indicator = 'blue_dot' AND value = 1
ORDER BY date DESC LIMIT 20;
```

3. **횡단면 검증**: 특정 날짜의 RS Rating 분포가 1~99에 고르게 분포하는지 확인
```sql
SELECT
  FLOOR(value/10)*10 as rs_range,
  COUNT(*) as cnt
FROM stock_indicators
WHERE indicator = 'ibd_rs_rating' AND date = '2026-02-06'
GROUP BY rs_range ORDER BY rs_range;
```
