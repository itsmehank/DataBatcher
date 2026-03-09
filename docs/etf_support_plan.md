# ETF 지원 추가 작업 계획서 (market = "ETF", 기존 테이블 재사용)

작성일: 2026-02-02

## 0. 결론 요약

- ETF는 `symbol_master.market = 'ETF'`로 저장한다.
- `asset_type` 컬럼은 추가하지 않는다.
- 
  - 일봉 가격: `stock_prices`
  - 일봉 지표: `stock_indicators`
  - 주봉 가격: `stock_prices_weekly`
  - 주봉 지표: `stock_indicators_weekly`

  **모두 기존 테이블을 그대로 재사용**한다.
- ETF 가격 수집은 주식과 API가 달라 **ETF 전용 Collector를 신규 생성**한다.
- `daily_update.py`, `bulk_update.py`는 `market == 'ETF'`일 때 **ETF Collector로 분기**한다.
- `weekly_update.py`, `bulk_update_weekly.py`는 DB의 `stock_prices`를 기반으로 집계하므로 **일봉만 ETF로 정상 적재되면 동일 로직으로 주봉 생성 가능**하다(단, market 검증/옵션에 ETF를 추가해야 한다).

---

## 1. 목표 / 비목표

### 1.1 목표

1) pykrx에서 ETF 종목 목록을 가져와 `symbol_master`에 적재
2) ETF 일봉 가격을 `stock_prices`에 적재
3) ETF도 기존과 동일하게 주봉 집계(`stock_prices_weekly`) 및 지표 적재(`stock_indicators*`)가 가능하도록 확장
4) 기존 stock 파이프라인(지표 계산/저장, 주봉 집계 등)을 최대한 그대로 재사용

### 1.2 비목표

- ETF의 상장 시장(KOSPI/KOSDAQ) 구분을 별도 컬럼으로 저장하지 않음
- ETF 전용 테이블을 만들지 않음
- ETF 전용 지표/지표명 규칙을 추가로 만들지 않음(기존 지표 파이프라인/스펙을 그대로 적용)

---

## 2. 사전 확인(이미 확인된 사실)

### 2.1 pykrx ETF 목록/이름 조회 가능

- `pykrx.stock.get_etf_ticker_list(date)` 로 ETF 티커 목록 조회 가능
- `pykrx.stock.get_etf_ticker_name(ticker)` 로 ETF 종목명 조회 가능
- ETF 티커는 숫자 6자리만 있는 것이 아니라 예: `0120J0` 같이 **문자 포함**도 존재할 수 있으므로,
  - 심볼은 항상 문자열로 취급한다.

### 2.2 pykrx ETF 가격 조회 API (기간/티커 기준)

- `pykrx.stock.get_etf_ohlcv_by_date(fromdate, todate, ticker, freq='d')` 사용 (기간+단일 티커)
- 참고: `get_etf_ohlcv_by_ticker(date)` 는 “특정 일자 전체 ETF” 조회용이므로 daily/bulk 흐름에 부적합

---

## 3. 구현 아키텍처

### 3.1 상태/데이터 모델

- `symbol_master.market`: 기존(KOSPI/KOSDAQ/KONEX) + 신규(ETF)
- `stock_prices.market`: `symbol_master.market` 값을 그대로 저장
  - 즉, ETF 종목의 `stock_prices.market`는 항상 `ETF`
- `source`: 기존과 동일하게 `'pykrx'`

### 3.2 Collector 구조

- 기존: `collectors/kr_stock.py` 의 `KRStockCollector`
- 신규: `collectors/kr_etf.py` 의 `KREtfCollector`

둘 다 동일한 “사용 형태”를 맞춘다:

- `fetch(symbol, start, end, market) -> pd.DataFrame`
- `save(df, symbol, mode='upsert'|'insert_only') -> int`

> 이유: `daily_update.py`, `bulk_update.py`에서 Collector 교체만으로 로직 재사용이 가능해짐

---

## 4. 파일별 작업 항목(실제 수정 단계)

### 4.1 `core/symbol_loader.py`

- [ ] `VALID_MARKETS`에 `'ETF'` 추가

성공 기준:
- `load_symbols_with_details(engine, market='ETF')` 호출이 ValueError 없이 동작

---

### 4.2 `scripts/sync_symbol_master.py` (ETF 목록 적재 로직 추가)

#### 4.2.1 요구사항

- [ ] 기존 주식 listing(pykrx_adapter.fetch_krx_listing) + 신규 ETF listing(`get_etf_ticker_list`)을 결합
- [ ] `symbol_master`에 신규/업데이트/상폐 상태를 반영
- [ ] ETF는 `market='ETF'`로 저장

#### 4.2.2 구현 상세

- [ ] `fetch_etf_listing(date_str: str | None = None) -> pd.DataFrame` 추가
  - 반환 컬럼: `symbol`, `Name`, `Market`
  - `Market`은 항상 `'ETF'`
- [ ] 기존 `fetch_krx_listing()` 결과와 `fetch_etf_listing()`을 `pd.concat`하여 “전체 listing”을 만들고,
  기존 `compare_and_classify()` / `upsert_symbol_master()` 흐름을 재사용

#### 4.2.3 충돌 정책(확정)

`symbol_master`의 PK가 `symbol` 단일이므로, listing 결합 시 동일 symbol이 두 번 등장하면 충돌.

- [ ] 정책(확정): **주식(기존 KOSPI/KOSDAQ/KONEX) 우선 유지, ETF는 스킵**
  - 즉, 동일 `symbol`이 (주식 listing)과 (ETF listing)에 동시에 존재하면,
    - `market != 'ETF'`인 row(주식)를 남기고
    - `market == 'ETF'`인 row는 제거(스킵)
- [ ] 충돌 로그(확정): `logs/sync_symbol_master_etf_conflicts.log`에 심볼 목록을 append로 기록
  - 예시 포맷:
    - `2026-02-02T18:00:00 | SYMBOL=000000 | kept=KOSPI | skipped=ETF`

> 이유: 의도치 않은 타입 변경(주식 → ETF)이 가장 위험한 장애 형태이기 때문

#### 4.2.4 상폐 처리(delisted) 안전장치(확정)

ETF listing API 실패/지연 등으로 결과가 비정상일 수 있으므로, ETF delist는 “추가 가드”를 둔다.

- [ ] 재시도(확정): ETF listing 호출을 최대 2회 재시도(짧은 backoff)
- [ ] 임계치 가드(확정): 아래 중 하나라도 만족하면, **이번 실행에서는 ETF delist 처리를 스킵**
  1) `len(etf_df) == 0`
  2) `len(etf_df) < 500` (초기 기준; 현재 관측치가 ~1000대이므로 절반 이하로 급감 시)
  3) `len(etf_df) < (prev_active_etf_count * 0.8)`
     - `prev_active_etf_count`는 DB에서
       `SELECT COUNT(*) FROM symbol_master WHERE status='ACTIVE' AND market='ETF'`로 조회

> 이유: 일시적 API 장애로 인한 “대량 DELISTED”를 예방하기 위함

---

### 4.3 `collectors/kr_etf.py` (신규)

#### 4.3.1 요구사항

- [ ] pykrx ETF OHLCV를 조회해서 `stock_prices` 스키마에 맞게 변환
- [ ] `market` 컬럼은 항상 `'ETF'`
- [ ] `source`는 `'pykrx'`
- [ ] 날짜는 `datetime.date` 로 변환(주식 Collector와 동일)

#### 4.3.2 구현 상세(확정 규칙)

- [ ] `fetch()`:
  - `fromdate/todate`는 `YYYYMMDD`로 변환 후 `stock.get_etf_ohlcv_by_date()` 호출
  - 반환 DF 컬럼 매핑(확정):
    - `시가 -> open`
    - `고가 -> high`
    - `저가 -> low`
    - `종가 -> close`
    - `거래량 -> volume`
  - 그 외 컬럼(확정: drop): `NAV`, `거래대금`, `기초지수` 등 스키마에 없는 값들은 저장하지 않음
  - `adj_close` 정책(확정): `adj_close = close`
  - `market`(확정): `'ETF'`
  - `source`(확정): `'pykrx'`
  - `date`(확정): `pd.to_datetime(...).dt.date`로 변환

- [ ] `save()`:
  - 기존 `DBManager.upsert_dataframe(..., table='stock_prices', mode=mode)` 재사용

---

### 4.4 `scripts/daily_update.py`

#### 4.4.1 CLI/market 검증

- [ ] `--market` choices에 `'ETF'` 추가

#### 4.4.2 Collector 분기

- [ ] 종목별 처리에서 `market == 'ETF'`이면 `KREtfCollector`를 사용하도록 분기
  - `--all` 모드: `load_symbols_with_details()`가 반환한 `market` 값으로 분기
  - `--symbols` 모드: `symbol_master`에서 조회한 `market` 값으로 분기

#### 4.4.3 저장 정책

- [ ] ETF 가격 적재 시 `market='ETF'`로 저장(Collector가 생성)
- [ ] 지표 저장은 기존대로 수행

추가 검증(확정): ETF 종목을 1개 처리한 뒤 아래 쿼리로 확인

- 가격 적재 확인:
  - `SELECT COUNT(*) FROM stock_prices WHERE symbol='<ETF>' AND market='ETF';`
- 지표 적재 확인(지표가 설정되어 있고 save=true인 경우):
  - `SELECT COUNT(*) FROM stock_indicators WHERE symbol='<ETF>' AND market='ETF' AND source='pykrx';`

---

### 4.5 `scripts/bulk_update.py`

#### 4.5.1 CLI/market 검증

- [ ] `--market`에 `'ETF'` 추가(이미 choices가 있다면)

#### 4.5.2 Collector 분기

- [ ] `symbol_master.market == 'ETF'` 인 종목은 `KREtfCollector` 사용

---

### 4.6 `scripts/weekly_update.py`

- [ ] `--market` choices에 `'ETF'` 추가

주의:
- weekly_update는 DB에서 `stock_prices`를 읽어 주봉 집계하므로,
  ETF 일봉이 `stock_prices`에 들어오기만 하면 주봉 집계는 자동 지원됨

추가 검증(확정): ETF 종목 1개에 대해 weekly_update 실행 후

- `SELECT COUNT(*) FROM stock_prices_weekly WHERE symbol='<ETF>' AND market='ETF';`

---

### 4.7 `scripts/bulk_update_weekly.py`

- [ ] `--market` 처리/검증에 `'ETF'` 지원 추가

구현 지침(확정):
- bulk_update_weekly의 CLI에 `--market` 파라미터가 이미 존재하면 choices에 `ETF`를 추가한다.
- bulk_update_weekly에 `--market` 파라미터가 없다면,
  - (1) CLI에 `--market`을 추가하고
  - (2) 심볼 로딩 SQL에 `AND market = :market` 필터를 적용한다.

주의:
- bulk_update_weekly 역시 DB 기반 집계

---

## 5. 테스트/검증 계획 (자동 테스트 우선)

### 5.1 네트워크/pykrx 의존을 최소화

- 단위 테스트는 mocking 위주
- 실제 pykrx 호출이 필요한 테스트는 최소 1~2개 스모크로 제한

### 5.2 테스트 목록

1) (이미 존재) `scripts/tests/test_pykrx_etf_listing.py`
   - ETF 티커 목록/이름 조회 가능
   - Market='ETF'로 변환 가능
   - 비숫자 티커 존재 가능성 확인

2) (추가 권장) market whitelist 테스트
   - `VALID_MARKETS`에 ETF가 포함되는지 assert

3) (추가 권장) daily/bulk 분기 테스트(모킹)
   - market='ETF'일 때 KREtfCollector.fetch 호출
   - market!='ETF'일 때 KRStockCollector.fetch 호출

4) (선택) 스모크 테스트(실제 API + 실제 DB)
   - ETF 1개 종목을 5~10 영업일만 수집해 `stock_prices`에 rows 생성 확인
   - 이후 `weekly_update --symbols <ETF>`로 주봉 생성 확인

---

## 6. 리스크 & 롤백

### 6.1 리스크

- ETF listing API 실패/빈 결과 시 대량 DELISTED 발생 위험
  - → 임계치/가드 필수
- 심볼 충돌(주식/ETF 동일 코드) 발생 시 타입 오염 위험
  - → 충돌은 스킵+로그로 처리

### 6.2 롤백

- `symbol_master`에서 `market='ETF'` 삭제
- `stock_prices`, `stock_prices_weekly`, `stock_indicators*`에서 `market='ETF'` 삭제
- 코드에서 `'ETF'` 지원 추가한 부분 제거

---

## 7. 작업 순서(권장)

1) market 검증/choices/VALID_MARKETS에 ETF 추가(실행이 안 막히도록)
2) `sync_symbol_master.py`에 ETF listing 적재 추가(충돌/상폐 가드 포함)
3) `collectors/kr_etf.py` 신규 생성
4) `daily_update.py` ETF collector 분기
5) `bulk_update.py` ETF collector 분기
6) `weekly_update.py`/`bulk_update_weekly.py` market 지원 확장
7) 테스트(단위→스모크)
