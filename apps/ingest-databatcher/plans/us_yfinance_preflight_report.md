# US FDR/yfinance Preflight Report

## 목적

`us_index_daily_update.py`(US-1)와 `us_daily_update.py`(US-2)에 `source_strategy`를 도입하기 전에,
현재 US 수집 파이프라인이 요구하는 입력/출력 계약을 `yfinance`가 만족할 수 있는지 사전 검증한 결과를 정리한다.

이번 문서는 구현 문서가 아니라 **사전 적합성 검토 결과** 문서다.

---

## 1. 현재 기준 계약

### 1-1. US 주식 수집 계약

기준 코드:

- `apps/ingest-databatcher/collectors/us_stock.py`
- `apps/ingest-databatcher/scripts/us_daily_update.py`
- `apps/ingest-databatcher/docs/database_schema.md`

입력 계약:

- `symbol`: 예) `AAPL`, `NVDA`, `SPY`, `BRK-B`
- `start`: `date` 객체 또는 `YYYY-MM-DD`
- `end`: `date` 객체 또는 `YYYY-MM-DD`
- `market`: `NYSE` / `NASDAQ` / `ETF`

정규화 후 기대 컬럼:

- `symbol`
- `date`
- `open`
- `high`
- `low`
- `close`
- `adj_close`
- `volume`
- `market`
- `source`

DB 적재 대상:

- `us_stock_prices`
- PK: `(symbol, date)`
- 저장 방식: `DBManager.upsert_dataframe(..., mode="insert_only"|"upsert")`

### 1-2. US 지수 수집 계약

기준 코드:

- `apps/ingest-databatcher/collectors/us_index.py`
- `apps/ingest-databatcher/scripts/us_index_daily_update.py`
- `apps/ingest-databatcher/docs/database_schema.md`

입력 계약:

- `symbol`: 내부 표준 심볼 `US500`, `DJI`, `IXIC`
- `start`: `date` 객체 또는 `YYYY-MM-DD`
- `end`: `date` 객체 또는 `YYYY-MM-DD`
- `market`: `SP500` / `DJI` / `IXIC`

정규화 후 기대 컬럼:

- `symbol`
- `date`
- `open`
- `high`
- `low`
- `close`
- `volume`
- `market`
- `source`

DB 적재 대상:

- `us_index_prices`
- PK: `(symbol, date)`

---

## 2. 수행한 사전 검증

### 2-1. import 가능 여부

실행 명령:

```bash
python -c "import yfinance, FinanceDataReader; print('ok')"
```

결과:

- `yfinance`, `FinanceDataReader` 모두 현재 환경에서 import 성공

### 2-2. 기존 FDR US 주식 probe 재확인

실행 명령:

```bash
python apps/ingest-databatcher/scripts/probes/fdr_us_stock_probe.py \
  --symbol AAPL --start 2025-12-01 --end 2025-12-10 --skip-listing
```

결과 요약:

- 행 수: 7
- 컬럼: `index`, `Open`, `High`, `Low`, `Close`, `Volume`, `Adj Close`
- `Adj Close` 존재
- `end=2025-12-10` 요청 시 마지막 거래일은 `2025-12-09`

판단:

- 현재 `USStockCollector`의 컬럼 매핑 로직과 일치
- 기존 FDR 계약은 명확함

### 2-3. FDR vs yfinance US 주식 일봉 직접 비교

실행 명령:

```bash
python apps/stock-alert-engine/scripts/probes/probe_us_provider.py \
  --symbol AAPL --start 2025-12-01 --end 2025-12-10
```

결과 요약:

- FDR:
  - 행 수: 7
  - 컬럼: `index`, `Open`, `High`, `Low`, `Close`, `Volume`, `Adj Close`
- yfinance:
  - 행 수: 7
  - 컬럼: `('Adj Close', 'AAPL')`, `('Close', 'AAPL')`, `('High', 'AAPL')`, `('Low', 'AAPL')`, `('Open', 'AAPL')`, `('Volume', 'AAPL')`
  - 일봉도 `MultiIndex columns` 반환
  - `end=2025-12-10` 요청 시 마지막 거래일은 `2025-12-09`

판단:

- **입력 인자는 충분하다.** `symbol`, `start`, `end`만으로 호출 가능하다.
- 단, `yfinance`는 현재 환경에서 **주식 일봉도 MultiIndex 컬럼 정규화가 필요**하다.
- `end`는 FDR과 동일하게 사실상 배타적으로 취급되는 형태로 관찰되었지만,
  구현 시에는 `yfinance`의 배타적 `end`를 명시적으로 처리하는 편이 안전하다.

### 2-4. 대표 종목군 입력 적합성 점검

실행 명령:

```bash
python -c "import FinanceDataReader as fdr; symbols=['AAPL','KO','SPY','BRK-B'];
for s in symbols:
    try:
        df=fdr.DataReader(s, start='2025-12-01', end='2025-12-10')
        print('FDR', s, 'rows', 0 if df is None else len(df), 'cols', [] if df is None else list(df.reset_index().columns))
    except Exception as e:
        print('FDR', s, 'ERROR', e)
"

python -c "import yfinance as yf; symbols=['AAPL','KO','SPY','BRK-B'];
for s in symbols:
    try:
        df=yf.download(s, start='2025-12-01', end='2025-12-10', auto_adjust=False, progress=False)
        print('YF', s, 'rows', 0 if df is None else len(df), 'cols', [] if df is None else list(df.columns))
    except Exception as e:
        print('YF', s, 'ERROR', e)
"
```

결과 요약:

- `AAPL`, `KO`, `SPY`, `BRK-B` 모두 FDR/yfinance 양쪽에서 응답 성공
- `BRK-B` 같은 하이픈 심볼도 현재 방식으로 그대로 호출 가능
- yfinance는 모든 케이스에서 MultiIndex 컬럼 반환

판단:

- 현재 `us_symbol_master.symbol` 형태가 일반적인 US stock/ETF 입력값으로는 충분할 가능성이 높다.
- 다만 전 종목 수준에서는 특수 심볼(`.` 포함, 클래스주, 선호주, 해외 ADR 변형) 샘플을 추가 검증하는 것이 바람직하다.

### 2-5. FDR US 지수 probe 재확인

실행 명령:

```bash
python apps/ingest-databatcher/scripts/probes/fdr_us_index_probe.py \
  --all-indices --start 2025-12-01 --end 2025-12-10
```

결과 요약:

- `US500`, `DJI`, `IXIC` 모두 응답 성공
- 각 응답 컬럼: `Open`, `High`, `Low`, `Close`, `Volume`, `Adj Close`
- 현재 collector는 `Adj Close`를 버리고 `volume`은 유지

판단:

- FDR 지수 응답은 현재 `USIndexCollector` 정규화 로직과 호환됨

### 2-6. yfinance US 지수 입력/출력 적합성 점검

실행 명령:

```bash
python -c "import yfinance as yf; symbols=['^GSPC','^DJI','^IXIC'];
for s in symbols:
    df = yf.download(s, start='2025-12-01', end='2025-12-10', auto_adjust=False, progress=False)
    print('SYMBOL', s)
    print('shape', df.shape)
    print('columns', list(df.columns))
    print('index_start', df.index[0] if not df.empty else None)
    print('index_end', df.index[-1] if not df.empty else None)
"
```

결과 요약:

- `^GSPC`, `^DJI`, `^IXIC` 모두 응답 성공
- 모든 지수에서 MultiIndex 컬럼 반환
- `Adj Close`, `Close`, `High`, `Low`, `Open`, `Volume` 포함
- `end=2025-12-10` 요청 시 마지막 거래일은 `2025-12-09`

판단:

- **입력 인자 자체는 충분하지 않다.** 내부 심볼 `US500`, `DJI`, `IXIC`를 그대로 넣으면 안 되고,
  provider 전용 매핑 계층이 필요하다.
- 권장 매핑:
  - `US500` -> `^GSPC`
  - `DJI` -> `^DJI`
  - `IXIC` -> `^IXIC`

---

## 3. 사전 결론

### 3-1. US 주식 (`us_daily_update.py` / `us_stock_prices`)

결론: **도입 가능성 높음**

이유:

- 현재 입력값(`symbol`, `start`, `end`, `market`)으로 `yfinance` 호출 가능
- 대표 주식/ETF/하이픈 심볼 샘플에서 모두 응답 성공
- `Adj Close`, `Close`, `Volume`을 모두 받을 수 있어 현재 DB 스키마에 맞출 수 있음

필수 보정:

- MultiIndex 컬럼 1차원 flatten
- 첫 날짜 컬럼을 `date`로 정규화
- `source='yfinance'` 저장
- `end` 배타 처리 명시화

### 3-2. US 지수 (`us_index_daily_update.py` / `us_index_prices`)

결론: **도입 가능성 높음, 단 symbol resolver 필수**

이유:

- yfinance도 지수 OHLCV 응답 가능
- `volume`도 현재 샘플에서는 존재
- 현재 DB 스키마가 요구하는 컬럼 집합으로 정규화 가능

필수 보정:

- 내부 심볼 -> yfinance ticker 매핑 계층 추가
- MultiIndex flatten
- `Adj Close`는 현재 스키마에 맞게 버림
- `source='yfinance'` 저장

---

## 4. 이번 사전 검증에서 확인된 핵심 리스크

1. `yfinance` 일봉이 현재 환경에서 단일 티커여도 MultiIndex 컬럼을 반환함
2. `end` 날짜 처리를 명시적으로 맞추지 않으면 provider별 일자 차이가 생길 수 있음
3. US index는 내부 심볼을 직접 넣을 수 없고 provider 전용 ticker 매핑이 필요함
4. `Adj Close` 의미는 downstream(`RS`, `Minervini`)에 직접 영향이 있으므로 `auto_adjust=False`를 고정하고 raw `Close`와 `Adj Close`를 분리 저장해야 함
5. 현재 샘플은 성공 케이스 중심이므로, 전 종목 전략 도입 전에는 특수 ticker 샘플 추가 검증이 필요함

---

## 5. 구현 전 필수 추가 검증 항목

아래는 구현 전에 별도 probe/test로 더 확인해야 하는 항목이다.

1. 특수 심볼 샘플
   - 점(`.`), 하이픈(`-`), ETF, 클래스주, 상장폐지 근접 종목
2. 컬럼 안정성
   - `Adj Close` 누락 사례 존재 여부
   - `Volume` dtype / NULL 처리
3. 날짜 경계
   - 동일 요청 기간에서 provider별 마지막 거래일 일치 여부
4. 지수 매핑 안정성
   - `US500`, `DJI`, `IXIC` 외 확장 가능성 여부
5. DB 적재 적합성
   - 현재 collector 기대 컬럼 순서로 DataFrame 재구성 후 `DBManager.upsert_dataframe()`에 그대로 전달 가능한지

---

## 6. 현재 판단

현재 시점의 기술적 판단은 아래와 같다.

- `yfinance`는 **현재 US-1 / US-2 구조에 들어갈 수 있는 수준의 호환성**이 있다.
- 다만 이는 "그대로 drop-in"은 아니고,
  **provider adapter + symbol resolver + column normalizer**를 추가해야 성립한다.
- 따라서 바로 구현에 들어가기보다,
  이 문서를 근거로 **구현 게이트가 있는 작업 계획**을 세운 뒤 진행하는 것이 맞다.
