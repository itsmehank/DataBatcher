# US 주식 분할/병합 대응 가격 데이터 갱신 계획

작성일: 2026-04-29

## 1. 배경

현재 US 주식 일봉 적재는 `daily_us.sh`를 통해 다음 순서로 실행된다.

```bash
python apps/ingest-databatcher/scripts/us_index_daily_update.py --all
python apps/ingest-databatcher/scripts/us_daily_update.py --all --with-indicators
python apps/ingest-databatcher/scripts/us_rs_update.py --days 7
python apps/ingest-databatcher/scripts/us_minervini_update.py --days 7
```

US 주식 가격 적재의 핵심 경로는 다음과 같다.

- `apps/ingest-databatcher/scripts/us_daily_update.py`
- `apps/ingest-databatcher/scripts/us_bulk_update.py`
- `apps/ingest-databatcher/collectors/us_stock.py`

두 스크립트 모두 `USStockCollector.fetch()`를 통해 가격을 수집한다. 기본 설정은 `apps/ingest-databatcher/config/settings.yaml`의 `collectors.us_stock.source_strategy: fdr`이며, 실제 원천은 `FinanceDataReader.DataReader()`다.

## 2. 확인된 문제

`CLSM` 종목에서 2025년 10월 말 가격 불연속이 확인되었다.

검증용 별도 스크립트:

```bash
python apps/ingest-databatcher/scripts/tests/probe_us_source_price_clsm.py \
  --symbol CLSM --market ETF --start 2025-10-20 --end 2025-10-31
```

확인 결과:

```text
FDR 현재 원본:
2025-10-24 close = 23.5760
2025-10-27 close = 23.7500
gap = +0.74%

DB 현재 저장값:
2025-10-24 close = 2.9470
2025-10-27 close = 23.7500
gap = +705.90%
```

거래량도 반대 방향으로 약 8배 차이가 난다.

```text
2025-10-24 volume
FDR 현재 원본: 6,400
DB 저장값: 51,200
```

이는 주식 병합/역분할 이후 과거 가격이 조정되었지만, DB에는 조정 전 값이 남아 있는 전형적인 패턴이다.

## 3. 현재 구조의 원인

현재 일일 적재는 최근 구간만 수집하고 가격 저장은 `insert_only`를 사용한다.

`us_daily_update.py`:

- 기본 조회 범위: `LOOKBACK_DAYS = 50`
- 가격 저장: `DBManager.upsert_dataframe(..., mode="insert_only")`

`us_bulk_update.py`:

- 지정 기간 일괄 수집
- 가격 저장: `collector.save(..., mode="insert_only")`

이 구조에서는 다음 문제가 발생한다.

1. 이미 저장된 날짜의 가격은 수정되지 않는다.
2. 데이터 공급자가 과거 가격을 split-adjusted 값으로 재보정해도 DB는 기존 값을 유지한다.
3. 최근 30~50일만 `upsert`로 바꿔도 split date 이전 전체 히스토리는 여전히 과거 미보정 값으로 남을 수 있다.
4. 지표, RS, Minervini 결과는 가격 데이터의 연속성을 전제로 하므로 가격 불연속이 남으면 후속 계산도 왜곡된다.

## 4. 매일 전체 히스토리 재적재는 적절한가

매일 전체 US 종목의 전체 히스토리를 재적재하는 방식은 권장하지 않는다.

이유:

- 전체 종목 수와 히스토리 길이에 비례해 API 호출량이 급증한다.
- 무료/비공식 데이터 소스는 rate limit과 일시 장애 가능성이 있다.
- 대부분의 종목은 매일 과거 전체 가격이 바뀌지 않는다.
- 지표/RS/Minervini 재계산 비용도 함께 증가한다.

대신 일반적으로는 다음 구조가 더 적절하다.

```text
일일 증분 가격 수집
+ corporate action 감지
+ 이벤트 발생 종목만 전체 히스토리 재동기화
```

## 5. 권장 해결 방향

### 5.1 일일 가격 수집은 최근 구간 upsert로 변경

현재 `insert_only`는 기존 데이터를 보존한다는 장점이 있지만, 최근 데이터 정정에는 취약하다.

권장:

- 최근 30~60일 가격은 `upsert`
- 장기 히스토리는 이벤트 감지 시에만 별도 갱신

주의:

- 이 변경만으로 split 문제 전체가 해결되지는 않는다.
- split date가 lookback 이전이면 과거 구간은 계속 미보정 상태로 남는다.

### 5.2 corporate action 감지 배치 추가

주식 분할/병합 이벤트를 별도로 감지하는 스크립트를 둔다.

후보 소스:

- `yfinance.Ticker(symbol).get_splits(period="max")`
- `yfinance.Ticker(symbol).splits`
- `yfinance.Ticker(symbol).get_actions(period="max")`
- `yf.download(symbol, ..., actions=True)`

장점:

- Python 패키지로 간단히 구현 가능
- split ratio와 날짜를 얻을 수 있음
- 현재 프로젝트에 이미 `yfinance` 의존성이 있으므로 도입 비용이 낮음

주의:

- Yahoo/yfinance는 무료 데이터 소스이며 공식 SLA가 없다.
- 이벤트 반영이 지연되거나 누락될 수 있다.
- 따라서 가격 불연속 감지 fallback을 함께 두는 것이 좋다.

### 5.3 split 이벤트 테이블 추가

감지한 이벤트를 별도 테이블에 저장한다.

예시:

```sql
CREATE TABLE IF NOT EXISTS us_corporate_actions (
  symbol        VARCHAR(32) NOT NULL,
  action_date   DATE NOT NULL,
  action_type   VARCHAR(32) NOT NULL,
  ratio         DECIMAL(18,8) NULL,
  source        VARCHAR(32) NOT NULL,
  detected_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  processed_at  DATETIME NULL,
  note          VARCHAR(512) NULL,
  PRIMARY KEY (symbol, action_date, action_type, source),
  KEY idx_processed_at (processed_at),
  KEY idx_action_date (action_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

`action_type` 예:

- `SPLIT`
- `REVERSE_SPLIT`
- `SUSPECTED_SPLIT`

`ratio` 예:

- 2-for-1 split: `2.0`
- 1-for-8 reverse split: `0.125` 또는 source 원본 기준 ratio를 그대로 저장

ratio 방향은 구현 전에 명확히 표준화해야 한다.

### 5.4 refresh queue 추가

이벤트 감지와 히스토리 재동기화를 분리하기 위해 queue 테이블을 둔다.

예시:

```sql
CREATE TABLE IF NOT EXISTS us_price_refresh_queue (
  id             BIGINT AUTO_INCREMENT PRIMARY KEY,
  symbol         VARCHAR(32) NOT NULL,
  market         VARCHAR(16) NOT NULL,
  reason         VARCHAR(64) NOT NULL,
  action_date    DATE NULL,
  status         VARCHAR(16) NOT NULL DEFAULT 'PENDING',
  requested_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  started_at     DATETIME NULL,
  finished_at    DATETIME NULL,
  error_message  VARCHAR(1024) NULL,
  UNIQUE KEY uq_pending_symbol_reason_date (symbol, reason, action_date),
  KEY idx_status_requested (status, requested_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

## 6. 신규 배치 설계

### 6.1 `us_detect_corporate_actions.py`

역할:

- `us_symbol_master`의 ACTIVE 종목을 대상으로 split/action 데이터를 조회
- 신규 split 이벤트를 `us_corporate_actions`에 저장
- 처리되지 않은 신규 이벤트를 `us_price_refresh_queue`에 적재

주요 옵션:

```bash
python apps/ingest-databatcher/scripts/us_detect_corporate_actions.py --days 14
python apps/ingest-databatcher/scripts/us_detect_corporate_actions.py --symbols CLSM
python apps/ingest-databatcher/scripts/us_detect_corporate_actions.py --market ETF
```

감지 범위:

- 기본은 최근 14~30일
- 초기 도입 시에는 `period=max`로 전체 이벤트를 한 번 백필하고, 이후 증분 감지

### 6.2 가격 불연속 fallback 감지

split API 누락에 대비해 가격 기반 감지도 추가한다.

기본 아이디어:

- 최근 90~120일 DB 가격에서 close-to-close 변화율 계산
- 절대 변화율이 임계값 이상이면 후보로 표시
- 거래량 변화율이 반대 방향의 split ratio와 유사하면 신뢰도 상승

예시 기준:

```text
abs(close_change) >= 50%
또는 close ratio가 2, 3, 4, 5, 8, 10 등 split ratio 근처
```

이 방식은 진짜 급등락과 split을 혼동할 수 있으므로 `SUSPECTED_SPLIT`으로 저장하고, 가능하면 yfinance split 이벤트와 교차 검증한다.

### 6.3 `us_refresh_adjusted_history.py`

역할:

- queue에서 `PENDING` 종목을 가져옴
- 해당 종목의 전체 일봉 히스토리를 원천에서 재수집
- 기존 `us_stock_prices`를 갱신
- 관련 지표/RS/Minervini 재계산 작업을 후속 실행

갱신 방식 후보:

1. `upsert` 전체 기간
   - 장점: 단순하고 기존 테이블 유지
   - 단점: 원천에서 사라진 과거 row를 삭제하지 못함

2. symbol 단위 delete 후 insert
   - 장점: 원천과 DB를 완전히 맞추기 쉬움
   - 단점: 중간 실패 시 해당 종목 데이터 공백 위험

3. staging table 사용 후 교체
   - 장점: 가장 안전
   - 단점: 구현 복잡도 증가

권장:

- 초기 구현은 `upsert` 전체 기간
- 안정화 후 `staging -> transaction replace` 방식 검토

주요 옵션:

```bash
python apps/ingest-databatcher/scripts/us_refresh_adjusted_history.py --queued
python apps/ingest-databatcher/scripts/us_refresh_adjusted_history.py --symbols CLSM --start 2000-01-01
python apps/ingest-databatcher/scripts/us_refresh_adjusted_history.py --symbols CLSM --recompute-indicators
```

## 7. daily_us.sh 통합안

권장 실행 순서:

```bash
run_step "US-1" "$PYTHON_BIN" apps/ingest-databatcher/scripts/us_index_daily_update.py --all
run_step "US-2" "$PYTHON_BIN" apps/ingest-databatcher/scripts/us_daily_update.py --all --with-indicators
run_step "US-2A" "$PYTHON_BIN" apps/ingest-databatcher/scripts/us_detect_corporate_actions.py --days 14
run_step "US-2B" "$PYTHON_BIN" apps/ingest-databatcher/scripts/us_refresh_adjusted_history.py --queued --with-indicators
run_step "US-3" "$PYTHON_BIN" apps/ingest-databatcher/scripts/us_rs_update.py --days 30
run_step "US-4" "$PYTHON_BIN" apps/ingest-databatcher/scripts/us_minervini_update.py --days 30
```

주의:

- split으로 전체 히스토리가 바뀐 종목은 RS/Minervini도 영향을 받는다.
- 단순히 `--days 7`만 재계산하면 과거 지표 왜곡이 남을 수 있다.
- split 이벤트 발생 종목은 별도 재계산 범위를 넓히거나 전체 재계산하는 옵션이 필요하다.

## 8. 단계별 구현 계획

### Phase 1. 진단/검증 도구 정리

- `probe_us_source_price_clsm.py`를 일반화해 임의 종목/기간 조회 가능하게 유지
- DB 값과 원천 값을 비교하는 dry-run 스크립트 추가
- close/volume ratio 기반 suspected split 리포트 생성

완료 기준:

- 특정 종목의 원천 FDR 값, collector normalize 값, DB 값을 한 번에 비교 가능
- split 의심 구간을 사람이 확인할 수 있는 출력 제공

### Phase 2. corporate action 테이블 및 감지 배치

- `us_corporate_actions` 테이블 추가
- `us_price_refresh_queue` 테이블 추가
- `us_detect_corporate_actions.py` 구현
- yfinance splits/actions 조회
- 신규 이벤트만 queue에 적재

완료 기준:

- `CLSM` 같은 split 이벤트 종목이 queue에 들어감
- 동일 이벤트 중복 적재 방지
- 네트워크 실패 종목은 로그에 남기고 전체 작업은 계속 진행

### Phase 3. 종목 단위 전체 가격 refresh

- `us_refresh_adjusted_history.py` 구현
- queue 기반 처리
- `--symbols` 수동 처리 지원
- 전체 히스토리 upsert
- 성공/실패 상태 업데이트

완료 기준:

- `CLSM` 전체 히스토리를 현재 원천 기준으로 갱신 가능
- refresh 후 2025-10-24와 2025-10-27 사이 가격 불연속 제거
- 실패 시 queue에 에러 메시지 저장

### Phase 4. 후속 지표 재계산 연동

- refresh된 종목의 `us_stock_indicators` 재계산
- 필요 시 `us_stock_indicators_weekly`도 재계산
- RS/Minervini 재계산 범위 정책 정리

완료 기준:

- 가격 갱신 후 차트의 SMA/RS Line이 왜곡되지 않음
- Dashboard/Minervini 결과가 갱신 가격을 기준으로 재생성됨

### Phase 5. daily_us.sh 통합 및 운영 안정화

- `daily_us.sh`에 감지/refresh 단계를 추가
- 기본은 dry-run 또는 queue-only로 시작
- 충분히 검증 후 자동 refresh 활성화
- 실패 로그와 요약 출력 추가

완료 기준:

- 매일 가격 수집과 별도로 split 이벤트 감지
- 이벤트 발생 종목만 자동/반자동 전체 히스토리 갱신
- 전체 US 종목 히스토리 재적재 없이 데이터 연속성 유지

## 9. 테스트 전략

단위 테스트:

- yfinance splits 응답 normalize 테스트
- 기존 이벤트 중복 방지 테스트
- queue upsert 테스트
- close/volume ratio 기반 suspected split 감지 테스트

DB 통합 테스트:

- `trade_test` 사용
- 임의 종목에 split 전후 불연속 가격 삽입
- refresh 실행 후 가격이 원천 mock 기준으로 갱신되는지 검증

수동 검증:

```bash
python apps/ingest-databatcher/scripts/tests/probe_us_source_price_clsm.py \
  --symbol CLSM --market ETF --start 2025-10-20 --end 2025-10-31
```

기대 결과:

- 원천과 DB의 2025-10-24 close가 같은 스케일이어야 함
- 2025-10-24 -> 2025-10-27 gap이 split ratio 수준이 아니라 정상 등락 수준이어야 함

## 10. 운영 정책 제안

권장 기본값:

- 일반 일일 가격 수집 lookback: 50일
- 최근 구간 저장 모드: `upsert`
- corporate action 감지 범위: 최근 14~30일
- suspected split 가격 검사 범위: 최근 120일
- split 이벤트 발생 종목 refresh 범위: 전체 히스토리

수동 개입이 필요한 경우:

- split API와 가격 불연속 감지가 서로 불일치
- 원천 데이터가 빈 값 또는 비정상 스케일로 응답
- ETF/ADR/상장폐지 종목처럼 이벤트 데이터가 불완전한 경우

## 11. 결론

현재 문제는 가격 수집 원천이 split-adjusted 값을 제공하지 못해서라기보다, 기존 DB 값이 `insert_only` 정책으로 갱신되지 않아 발생한 것으로 보인다.

따라서 해결책은 매일 전체 히스토리를 재수집하는 것이 아니라 다음 구조가 적절하다.

```text
최근 가격은 upsert
+ split/reverse split 이벤트 별도 감지
+ 이벤트 발생 종목만 전체 히스토리 refresh
+ 해당 종목 지표/RS/Minervini 재계산
```

이 방식은 현재 배치 구조와 잘 맞고, API 호출량과 재계산 비용을 통제하면서도 주식 분할/병합으로 인한 과거 가격 보정 문제를 해결할 수 있다.

---

## 12. 실용적 구현 가이드 — 코드 레벨

설계(§5~§8)를 실제 코드로 연결하는 참조 구현이다.
모든 코드는 현재 프로젝트 패키지(`yfinance`, `sqlalchemy`, `pandas`)만 사용한다.

---

### 12.1 yfinance로 split 이력 조회

`yfinance`는 이미 `us_sync_symbol_master.py`에서 사용 중이므로 추가 의존성이 없다.

```python
import yfinance as yf

ticker = yf.Ticker("CLSM")

# Series: DatetimeIndex → float (split ratio)
splits = ticker.splits
# 2025-10-27    0.125    ← 1/8 = 8:1 reverse split
# ratio 해석:
#   0.125 = 1/8  → 8:1 reverse split  (주식 8주 → 1주, 가격 ×8)
#   2.0   = 2/1  → 2:1 forward split  (주식 1주 → 2주, 가격 ×0.5)

# ratio 기준으로 reverse/forward 구분
for dt, ratio in splits.items():
    action_type = "REVERSE_SPLIT" if ratio < 1.0 else "SPLIT"
    print(f"{dt.date()}  {action_type}  ratio={ratio:.4f}")
```

**비율 표현 주의**: yfinance는 reverse split을 `1/N` 분수로 반환한다.
`0.125`를 DB에 저장할 때 그대로 저장하고, 조회 시 역수(`8.0`)로 환산하거나
`ratio_raw`와 `ratio_display` 컬럼을 분리하는 것이 명확하다.

---

### 12.2 최근 N일 이벤트만 조회

매일 감지 배치에서는 전체 이력이 아니라 최근 구간만 조회하는 것이 효율적이다.

```python
from datetime import date, timedelta
import yfinance as yf

def fetch_splits_since(symbol: str, since: date) -> list[dict]:
    """since 이후 발생한 split 이벤트 목록 반환."""
    ticker = yf.Ticker(symbol)
    splits = ticker.splits
    if splits.empty:
        return []

    recent = splits[splits.index.date >= since]
    return [
        {
            "symbol": symbol,
            "action_date": str(ts.date()),
            "action_type": "REVERSE_SPLIT" if ratio < 1.0 else "SPLIT",
            "ratio": float(ratio),
            "source": "yfinance",
        }
        for ts, ratio in recent.items()
    ]

# 사용 예 — 최근 14일
events = fetch_splits_since("CLSM", date.today() - timedelta(days=14))
# [{"symbol": "CLSM", "action_date": "2025-10-27",
#   "action_type": "REVERSE_SPLIT", "ratio": 0.125, "source": "yfinance"}]
```

---

### 12.3 DB 가격 기반 fallback 감지

yfinance API 누락을 보완한다. 하루 사이 close가 50% 이상 변하면 split 후보로 표시.

```python
from sqlalchemy import text
from sqlalchemy.orm import Session

def detect_price_discontinuity(
    symbol: str,
    db_session: Session,
    lookback_days: int = 120,
    threshold: float = 0.5,
) -> list[dict]:
    """
    close-to-close 비율이 threshold 이상 급변한 날짜를 반환.
    거래량 방향이 반대이면 split 신뢰도 상승.
    """
    rows = db_session.execute(text(
        "SELECT date, close, volume FROM us_stock_prices "
        "WHERE symbol = :sym "
        "ORDER BY date DESC LIMIT :n"
    ), {"sym": symbol, "n": lookback_days + 1}).fetchall()

    rows = sorted(rows, key=lambda r: r[0])  # ASC
    events = []

    for i in range(1, len(rows)):
        prev_close = float(rows[i - 1][1])
        curr_close = float(rows[i][1])
        if prev_close == 0:
            continue

        ratio = curr_close / prev_close
        if abs(ratio - 1.0) < threshold:
            continue  # 변화율 threshold 미만 → 정상 등락

        # 거래량 방향 cross-check
        prev_vol = int(rows[i - 1][2])
        curr_vol  = int(rows[i][2])
        vol_ratio = curr_vol / prev_vol if prev_vol > 0 else None

        # split: 가격 상승 + 거래량 감소 (reverse split)
        #        가격 하락 + 거래량 증가 (forward split)
        is_consistent = (
            vol_ratio is not None
            and (ratio > 1.0 and vol_ratio < 0.9)   # reverse split
            or  (ratio < 1.0 and vol_ratio > 1.1)   # forward split
        )

        events.append({
            "symbol": symbol,
            "action_date": str(rows[i][0]),
            "action_type": "SUSPECTED_SPLIT",
            "price_ratio": round(ratio, 4),
            "vol_ratio": round(vol_ratio, 4) if vol_ratio else None,
            "consistent": is_consistent,
            "source": "price_discontinuity",
        })

    return events
```

---

### 12.4 yfinance + DB fallback 교차 검증

두 소스를 결합해 신뢰도를 높인다.

```python
from datetime import date, timedelta

def get_verified_split_events(
    symbol: str,
    db_session,
    since: date,
) -> list[dict]:
    """
    yfinance 이벤트와 DB 가격 불연속을 교차 검증한다.
    양쪽 모두 감지하면 CONFIRMED, 한쪽만이면 SUSPECTED.
    """
    yf_events  = {e["action_date"]: e for e in fetch_splits_since(symbol, since)}
    db_events  = {e["action_date"]: e for e in detect_price_discontinuity(symbol, db_session)}

    all_dates = set(yf_events) | set(db_events)
    verified  = []

    for dt in sorted(all_dates):
        in_yf = dt in yf_events
        in_db = dt in db_events

        event = (yf_events.get(dt) or db_events.get(dt)).copy()
        event["confidence"] = "CONFIRMED" if (in_yf and in_db) else "SUSPECTED"
        event["yfinance_detected"] = in_yf
        event["price_detected"]    = in_db

        if in_yf:
            event["ratio"] = yf_events[dt]["ratio"]

        verified.append(event)

    return verified
```

---

### 12.5 `us_corporate_actions` 테이블에 저장

```python
from sqlalchemy import text
from datetime import datetime

def upsert_corporate_action(db_session, event: dict) -> None:
    """감지된 이벤트를 us_corporate_actions에 저장. 중복은 무시."""
    db_session.execute(text("""
        INSERT IGNORE INTO us_corporate_actions
          (symbol, action_date, action_type, ratio, source, detected_at, note)
        VALUES
          (:symbol, :action_date, :action_type, :ratio, :source, :detected_at, :note)
    """), {
        "symbol":      event["symbol"],
        "action_date": event["action_date"],
        "action_type": event.get("action_type", "UNKNOWN"),
        "ratio":       event.get("ratio"),
        "source":      event.get("source", "unknown"),
        "detected_at": datetime.now(),
        "note":        event.get("confidence"),
    })
    db_session.commit()
```

---

### 12.6 refresh queue 등록

```python
def enqueue_refresh(db_session, symbol: str, market: str, action_date: str) -> None:
    """split 발생 종목을 refresh queue에 적재. 동일 항목 중복 방지."""
    db_session.execute(text("""
        INSERT IGNORE INTO us_price_refresh_queue
          (symbol, market, reason, action_date, status, requested_at)
        VALUES
          (:symbol, :market, 'SPLIT_DETECTED', :action_date, 'PENDING', NOW())
    """), {"symbol": symbol, "market": market, "action_date": action_date})
    db_session.commit()
```

---

### 12.7 전체 가격 히스토리 재수집 (refresh)

```python
import FinanceDataReader as fdr
from datetime import date

def refresh_symbol_price_history(
    symbol: str,
    db_session,
    db_manager,           # ingest-databatcher DBManager
    start: str = "2000-01-01",
) -> int:
    """
    종목 전체 일봉을 원천(FDR)에서 재수집해 us_stock_prices를 upsert.
    반환: 처리된 행 수.
    """
    df = fdr.DataReader(symbol, start=start, end=str(date.today()))
    if df is None or df.empty:
        return 0

    df = df.reset_index().rename(columns={
        "Date": "date", "Open": "open", "High": "high",
        "Low": "low",   "Close": "close", "Adj Close": "adj_close",
        "Volume": "volume",
    })
    df["symbol"] = symbol
    df["market"] = "NASDAQ"   # 실제 구현 시 us_symbol_master에서 조회
    df["source"] = "fdr"

    db_manager.upsert_dataframe(df, "us_stock_prices", mode="upsert")
    return len(df)
```

---

### 12.8 `daily_us.sh`에 삽입할 감지 스크립트 骨格

위 함수들을 `us_detect_corporate_actions.py`로 조합하면:

```python
# apps/ingest-databatcher/scripts/us_detect_corporate_actions.py
import argparse
from datetime import date, timedelta

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=14,
                        help="최근 N일 이내 이벤트 감지")
    parser.add_argument("--symbols", nargs="+", default=None,
                        help="특정 종목만 처리 (기본: ACTIVE 전체)")
    parser.add_argument("--dry-run", action="store_true",
                        help="감지만 하고 DB에 저장하지 않음")
    args = parser.parse_args()

    since = date.today() - timedelta(days=args.days)
    # ... symbol 목록 로드, 루프, 감지, 저장 ...
    # 네트워크 실패 종목은 except + sync_log WARN 후 continue

if __name__ == "__main__":
    main()
```

`daily_us.sh` 삽입 위치 (§7 참조):

```bash
run_step "US-2A" "$PYTHON_BIN" \
  apps/ingest-databatcher/scripts/us_detect_corporate_actions.py --days 14
run_step "US-2B" "$PYTHON_BIN" \
  apps/ingest-databatcher/scripts/us_refresh_adjusted_history.py --queued --with-indicators
```

---

### 12.9 소스별 비교표

| 방법 | US | KR | 구현 난이도 | 비용 | 비고 |
|---|---|---|---|---|---|
| `yfinance.splits` | ✅ | ❌ | 낮음 | 무료 | 이미 프로젝트에 설치됨 |
| DB 가격 비율 감지 | ✅ | ✅ | 낮음 | 없음 | fallback용, false positive 주의 |
| DART Open API | ❌ | ✅ | 높음 | 무료 | corp_code 매핑 필요 |
| Polygon.io API | ✅ | ❌ | 중간 | 유료 | 공식 SLA 있음 |

**현재 프로젝트 권장**: US는 `yfinance.splits` + DB 가격 비율 교차 검증.
KR 대응은 별도 ADR 결정 후 진행.

