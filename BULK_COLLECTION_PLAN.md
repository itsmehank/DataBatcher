# 전체 종목 자동 수집 기능 구현 계획

## 📋 문서 정보
- 작성일: 2026-01-17
- 버전: v1.0
- 상태: 검토 대기 (Review Pending)

---

## 1. 개요

### 1.1 목표
현재 수동으로 심볼을 입력해야 하는 방식을 개선하여, 전체 KRX 종목(약 2,894개)을 자동으로 수집하는 시스템 구축

### 1.2 현재 문제점
```bash
# ❌ 현재: 모든 종목을 일일이 입력해야 함
python scripts/daily_update.py --symbols 005930 000660 373220 ... (2894개)

# ❌ 신규 상장/상장폐지 종목 수동 관리 필요
# ❌ 전체 기간 데이터 일괄 수집 방법 없음
```

### 1.3 예상 결과
```bash
# ✅ 목표: 간단한 명령으로 전체 종목 수집
python scripts/bulk_update.py --start 2020-01-01 --end 2024-12-31

# ✅ 일일 업데이트도 --all 옵션으로 간편화
python scripts/daily_update.py --all --force

# ✅ 종목 마스터 자동 동기화
python scripts/sync_symbol_master.py  # 주 1회 실행
```

---

## 2. 솔루션 아키텍처

### 2.1 전체 구조도
```
┌─────────────────────────────────────────────────────────┐
│ 1. 종목 마스터 관리 (신규 스크립트)                         │
│    scripts/sync_symbol_master.py                        │
│                                                         │
│    [FDR] → StockListing('KRX') → symbol_master 테이블    │
│    - 신규 상장 종목 추가                                   │
│    - 상장폐지 종목 상태 변경 (status=DELISTED)            │
│    - 시가총액/섹터 등 메타데이터 업데이트                    │
└─────────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│ 2. 전체 종목 일괄 수집 (신규 스크립트)                       │
│    scripts/bulk_update.py                               │
│                                                         │
│    [symbol_master] → 배치 처리 → [collectors] → [DB]     │
│    - ThreadPoolExecutor로 병렬 처리                       │
│    - tqdm 프로그레스바로 진행상황 표시                       │
│    - 실패한 종목은 로그 기록 후 계속 진행                     │
└─────────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│ 3. 기존 스크립트 개선                                       │
│    scripts/daily_update.py                              │
│                                                         │
│    옵션 추가:                                             │
│    --all          : 전체 ACTIVE 종목                      │
│    --market KOSPI : 특정 마켓만                           │
│    --top 100      : 시가총액 상위 N개                      │
└─────────────────────────────────────────────────────────┘
```

### 2.2 데이터베이스 활용
- **symbol_master** 테이블 (이미 존재)
  - 전체 종목 목록의 단일 진실 공급원(Single Source of Truth)
  - status 필드로 ACTIVE/DELISTED/IPO_PENDING 구분
  - Marcap(시가총액) 필드로 정렬/필터링 가능

---

## 3. Phase별 구현 계획

### Phase 1: 종목 마스터 동기화 스크립트

#### 3.1.1 파일 생성
**경로**: `scripts/sync_symbol_master.py`

#### 3.1.2 주요 기능
```python
# 핵심 로직 흐름
def sync_symbol_master():
    """
    1. FDR에서 전체 종목 목록 가져오기
    2. DB의 기존 종목과 비교
    3. 신규 종목 추가 (status=ACTIVE)
    4. 누락된 종목 상장폐지 처리 (status=DELISTED)
    5. 메타데이터 업데이트 (name, marcap 등)
    """
    pass
```

#### 3.1.3 상세 함수 시그니처
```python
def fetch_krx_listing() -> pd.DataFrame:
    """
    FDR에서 전체 KRX 종목 목록 가져오기

    Returns:
        DataFrame with columns:
        - Code: 종목코드 (str)
        - Name: 종목명 (str)
        - Market: KOSPI/KOSDAQ/KONEX (str)
        - Marcap: 시가총액 (int)
        - Stocks: 상장주식수 (int)
    """
    return fdr.StockListing('KRX')


def compare_and_classify(
    fdr_df: pd.DataFrame,
    db_symbols: set
) -> tuple[pd.DataFrame, pd.DataFrame, set]:
    """
    FDR 종목과 DB 종목을 비교하여 분류

    Args:
        fdr_df: FDR에서 가져온 전체 종목 DataFrame
        db_symbols: DB에 이미 있는 종목 코드 set

    Returns:
        (신규종목 DataFrame, 업데이트종목 DataFrame, 상장폐지종목 set)
    """
    pass


def upsert_symbol_master(
    engine: Engine,
    new_symbols: pd.DataFrame,
    update_symbols: pd.DataFrame,
    delisted_symbols: set
) -> dict[str, int]:
    """
    symbol_master 테이블 업데이트

    Returns:
        {"added": 50, "updated": 2800, "delisted": 44}
    """
    pass
```

#### 3.1.4 실행 예시
```bash
# 기본 실행 (전체 KRX)
python scripts/sync_symbol_master.py

# 출력 예시
[2026-01-17 10:00:00] Fetching KRX listing from FDR...
[2026-01-17 10:00:03] Fetched 2,894 symbols
[2026-01-17 10:00:03] Comparing with DB (2,850 existing symbols)...
[2026-01-17 10:00:04] Results:
  - New symbols: 50
  - Updated symbols: 2,800
  - Delisted symbols: 6
[2026-01-17 10:00:05] Sync completed successfully!
```

#### 3.1.5 예상 코드량
- 약 200-250 라인
- 의존성: FinanceDataReader, pandas, SQLAlchemy
- 소요 시간: 2-3시간

---

### Phase 2: 전체 종목 일괄 수집 스크립트

#### 3.2.1 파일 생성
**경로**: `scripts/bulk_update.py`

#### 3.2.2 주요 기능
```python
# 핵심 로직 흐름
def bulk_update(start: date, end: date, market: str, workers: int):
    """
    1. symbol_master에서 ACTIVE 종목 조회
    2. ThreadPoolExecutor로 병렬 처리
    3. tqdm으로 진행상황 표시
    4. 실패한 종목 로그 기록
    5. 최종 요약 리포트 출력
    """
    pass
```

#### 3.2.3 상세 함수 시그니처
```python
def load_symbols(
    engine: Engine,
    market: Optional[str] = None,
    top: Optional[int] = None
) -> list[tuple[str, str]]:
    """
    DB에서 수집 대상 종목 목록 로드

    Args:
        engine: SQLAlchemy engine
        market: KOSPI/KOSDAQ/ALL (default: ALL)
        top: 시가총액 상위 N개만 (default: None = 전체)

    Returns:
        [(symbol, name), ...] 리스트
    """
    pass


def collect_single_symbol(
    symbol: str,
    name: str,
    start: date,
    end: date,
    collector: KRStockCollector,
    pipeline: IndicatorPipeline,
    saver: IndicatorSaver
) -> dict:
    """
    단일 종목 수집 및 저장

    Returns:
        {
            "symbol": "005930",
            "name": "삼성전자",
            "status": "success",
            "price_rows": 252,
            "indicator_rows": 504,
            "error": None
        }
    """
    pass


def parallel_collect(
    symbols: list[tuple[str, str]],
    start: date,
    end: date,
    workers: int,
    rate_limit: float
) -> list[dict]:
    """
    병렬 처리로 전체 종목 수집

    Args:
        symbols: [(symbol, name), ...]
        start: 시작일
        end: 종료일
        workers: 병렬 워커 수
        rate_limit: 초당 요청 수 제한

    Returns:
        [결과 dict, ...]
    """
    with ThreadPoolExecutor(max_workers=workers) as executor:
        # Rate limiter + tqdm progress bar
        pass
```

#### 3.2.4 Rate Limiting 구현
```python
from threading import Semaphore
import time

class RateLimiter:
    """
    Thread-safe rate limiter
    초당 N개의 요청만 허용
    """
    def __init__(self, requests_per_second: float):
        self.interval = 1.0 / requests_per_second
        self.last_request = 0
        self.lock = threading.Lock()

    def acquire(self):
        with self.lock:
            elapsed = time.time() - self.last_request
            if elapsed < self.interval:
                time.sleep(self.interval - elapsed)
            self.last_request = time.time()
```

#### 3.2.5 실행 예시
```bash
# 전체 종목 과거 5년치 수집
python scripts/bulk_update.py \
    --start 2020-01-01 \
    --end 2024-12-31 \
    --workers 4 \
    --market ALL

# KOSPI만 수집
python scripts/bulk_update.py \
    --start 2023-01-01 \
    --end 2024-12-31 \
    --market KOSPI \
    --workers 8

# 시가총액 상위 100개만
python scripts/bulk_update.py \
    --start 2024-01-01 \
    --end 2024-12-31 \
    --top 100 \
    --workers 4

# 출력 예시
[2026-01-17 10:00:00] Loading symbols from symbol_master...
[2026-01-17 10:00:01] Loaded 2,844 ACTIVE symbols (market=ALL)
[2026-01-17 10:00:01] Starting bulk collection (2020-01-01 to 2024-12-31)
[2026-01-17 10:00:01] Workers: 4, Rate limit: 5.0 req/sec

Progress: 2844/2844 [============================] 100% | 12:34 elapsed

[2026-01-17 10:12:35] Summary:
  - Success: 2,830 symbols
  - Failed: 14 symbols (see logs/bulk_update_failed.log)
  - Total price rows: 3,587,600
  - Total indicator rows: 7,175,200
  - Duration: 12m 34s
```

#### 3.2.6 예상 코드량
- 약 300-350 라인
- 의존성: concurrent.futures, tqdm, threading
- 소요 시간: 4-5시간

---

### Phase 3: daily_update.py 개선

#### 3.3.1 기존 파일 수정
**경로**: `scripts/daily_update.py`

#### 3.3.2 추가할 argparse 옵션
```python
def parse_args(argv=None):
    p = argparse.ArgumentParser(description="KRX 일일 업데이트")

    # 기존 옵션
    p.add_argument("--symbols", nargs="*", default=None,
                   help="수집할 심볼 리스트 (미지정 시 --all 필요)")
    p.add_argument("--start", default=None, help="수집 시작일")
    p.add_argument("--end", default=None, help="수집 종료일")
    p.add_argument("--force", action="store_true", help="마감 체크 무시")

    # 신규 옵션
    p.add_argument("--all", action="store_true",
                   help="symbol_master의 모든 ACTIVE 종목 수집")
    p.add_argument("--market", choices=["KOSPI", "KOSDAQ", "KONEX", "ALL"],
                   default="ALL", help="수집할 마켓")
    p.add_argument("--top", type=int, default=None,
                   help="시가총액 상위 N개만 수집")

    return p.parse_args(argv)
```

#### 3.3.3 main() 함수 수정
```python
def main(argv=None):
    args = parse_args(argv)

    # Validation: --symbols 또는 --all 중 하나는 필수
    if not args.symbols and not args.all:
        print("Error: --symbols 또는 --all 중 하나를 지정해야 합니다.", file=sys.stderr)
        sys.exit(2)

    cfg = load_settings()
    engine = DBManager.get_engine(DBConfig(**cfg["database"]))

    # 종목 목록 결정
    if args.all:
        symbols = load_symbols_from_master(engine, args.market, args.top)
        print(f"Loaded {len(symbols)} symbols from symbol_master (market={args.market})")
    else:
        symbols = args.symbols

    # 기존 로직 (for loop) 유지
    for s in symbols:
        # ... 기존 수집 로직
```

#### 3.3.4 새로운 헬퍼 함수
```python
def load_symbols_from_master(
    engine: Engine,
    market: str = "ALL",
    top: Optional[int] = None
) -> list[str]:
    """
    symbol_master에서 ACTIVE 종목 코드 로드

    Args:
        engine: SQLAlchemy engine
        market: KOSPI/KOSDAQ/KONEX/ALL
        top: 시가총액 상위 N개만 (None = 전체)

    Returns:
        ["005930", "000660", ...]
    """
    sql = """
        SELECT symbol FROM symbol_master
        WHERE status = 'ACTIVE'
    """
    if market != "ALL":
        sql += f" AND market = '{market}'"

    sql += " ORDER BY Marcap DESC"

    if top:
        sql += f" LIMIT {top}"

    with engine.connect() as conn:
        result = conn.execute(text(sql))
        return [row[0] for row in result]
```

#### 3.3.5 실행 예시
```bash
# 전체 종목 일일 업데이트
python scripts/daily_update.py --all --force

# KOSPI만 업데이트
python scripts/daily_update.py --all --market KOSPI --force

# 시가총액 상위 200개만
python scripts/daily_update.py --all --top 200 --force

# 기존 방식도 여전히 작동
python scripts/daily_update.py --symbols 005930 000660 --force
```

#### 3.3.6 예상 코드량
- 약 50-70 라인 추가 (기존 코드 수정 포함)
- 소요 시간: 1-2시간

---

## 4. 파일 구조 요약

```
DataBatcher/
├── scripts/
│   ├── sync_symbol_master.py    ← 신규 (Phase 1)
│   ├── bulk_update.py            ← 신규 (Phase 2)
│   └── daily_update.py           ← 수정 (Phase 3)
│
├── core/
│   ├── rate_limiter.py           ← 신규 (Phase 2, 선택사항)
│   └── symbol_loader.py          ← 신규 (Phase 3, 공통 유틸)
│
└── logs/
    └── bulk_update_failed.log    ← 자동 생성 (Phase 2)
```

---

## 5. 예상 실행 시간

### 5.1 sync_symbol_master.py
- FDR API 호출: ~3초
- DB 비교 및 업데이트: ~2초
- **총 예상 시간: 약 5초**

### 5.2 bulk_update.py (전체 2,844개 종목, 1년치)
```
가정:
- FDR rate limit: 5 req/sec (config 기준)
- 병렬 워커: 4개
- 종목당 평균 처리 시간: 0.5초 (네트워크 + 계산 + DB 저장)

계산:
- Rate limit 제약: 2,844 / 5 = 568초 (약 9.5분)
- 병렬 처리 이득: 568 / 4 = 142초 (약 2.4분) ← 이론적 최소값
- 실제 처리 시간: 각 종목 0.5초 × 2,844 / 4 = 355초 (약 6분)

**총 예상 시간: 약 10-15분** (rate limit이 병목)
```

### 5.3 daily_update.py --all (당일 데이터만)
```
가정:
- 당일 데이터만 수집 (warmup 포함 약 30일치)
- 종목당 처리 시간: 0.3초

계산:
- Rate limit 제약: 2,844 / 5 = 568초 (약 9.5분)
- 병렬화 없음 (순차 처리): 2,844 × 0.3 = 853초 (약 14분)

**총 예상 시간: 약 15-20분**
```

---

## 6. 위험 요소 및 대응 방안

### 6.1 FDR API Rate Limit 초과
**위험**: 과도한 요청으로 차단 가능
**대응**:
- RateLimiter 클래스로 요청 간격 강제
- 설정 파일에서 rate_limit_per_sec 조정 가능
- 실패 시 exponential backoff 재시도

### 6.2 DB 연결 고갈
**위험**: 대량 병렬 처리 시 connection pool 고갈
**대응**:
- 워커 수를 pool_size보다 작게 제한
- config/settings.yaml에서 pool_size 증가 (기본 10 → 20)

### 6.3 중간 실패 시 재시작
**위험**: 2,000번째 종목에서 실패 시 처음부터 다시 시작?
**대응**:
- 이미 저장된 종목은 upsert로 자동 스킵
- 실패한 종목만 별도 로그에 기록
- `--retry-failed` 옵션으로 실패 목록만 재시도

### 6.4 신규 상장 종목 누락
**위험**: sync_symbol_master.py를 실행하지 않으면 신규 종목 수집 안 됨
**대응**:
- 주 1회 자동 실행 (cron/systemd timer)
- daily_update.py에 경고 메시지 추가:
  ```
  Warning: Last symbol_master sync was 10 days ago.
  Run 'python scripts/sync_symbol_master.py' to update.
  ```

---

## 7. 테스트 계획

### 7.1 Unit Test (선택사항)
```python
# tests/test_symbol_master.py
def test_fetch_krx_listing():
    df = fetch_krx_listing()
    assert len(df) > 2500
    assert "Code" in df.columns
    assert "Market" in df.columns

def test_compare_and_classify():
    # Mock 데이터로 신규/업데이트/상장폐지 분류 로직 검증
    pass
```

### 7.2 Integration Test (필수)
```bash
# 1. 소규모 테스트 (10개 종목)
python scripts/sync_symbol_master.py
python scripts/bulk_update.py --top 10 --start 2024-01-01 --end 2024-12-31

# 2. DB 검증
mysql -u YOUR_DB_USER -p market -e "SELECT COUNT(*) FROM stock_prices;"
mysql -u YOUR_DB_USER -p market -e "SELECT COUNT(*) FROM stock_indicators;"

# 3. 전체 종목 테스트 (시간 소요)
python scripts/bulk_update.py --start 2024-01-01 --end 2024-12-31
```

### 7.3 Dry-run 모드 (권장)
```bash
# --dry-run 옵션 추가: DB에 저장하지 않고 시뮬레이션만
python scripts/bulk_update.py --start 2024-01-01 --end 2024-12-31 --dry-run

# 출력: "Would collect 2,844 symbols (0 rows saved, dry-run mode)"
```

---

## 8. 배포 및 운영

### 8.1 초기 설정 (1회)
```bash
# 1. 종목 마스터 초기화
python scripts/sync_symbol_master.py

# 2. 과거 데이터 일괄 수집 (시간 소요)
python scripts/bulk_update.py --start 2020-01-01 --end 2024-12-31 --workers 8
```

### 8.2 일일 운영
```bash
# 1. 매일 17:00 - 전체 종목 일일 업데이트
python scripts/daily_update.py --all --force

# 2. 매주 일요일 02:00 - 종목 마스터 동기화
python scripts/sync_symbol_master.py
```

### 8.3 cron 설정 예시
```bash
# crontab -e
# 평일 17:00 - 전체 종목 일일 업데이트
0 17 * * 1-5 cd /path/to/DataBatcher && python scripts/daily_update.py --all >> logs/daily_update.log 2>&1

# 매주 일요일 02:00 - 종목 마스터 동기화
0 2 * * 0 cd /path/to/DataBatcher && python scripts/sync_symbol_master.py >> logs/sync_symbols.log 2>&1
```

---

## 9. 예상 영향도

### 9.1 기존 코드 영향
- ✅ **core/**: 영향 없음 (신규 모듈만 추가)
- ✅ **collectors/**: 영향 없음 (기존 KRStockCollector 그대로 사용)
- ✅ **indicators/**: 영향 없음
- ⚠️ **scripts/daily_update.py**: 수정 필요 (하위 호환성 유지)
- ✅ **config/**: 영향 없음 (필요 시 rate_limit 조정만)

### 9.2 데이터베이스 영향
- ✅ **symbol_master**: 데이터 채워짐 (현재 비어있음)
- ✅ **stock_prices**: 대량 데이터 적재 (수십만~수백만 행)
- ✅ **stock_indicators**: 대량 데이터 적재 (수백만 행)
- ⚠️ **디스크 공간**: 약 5GB 추가 필요 (5년치 전체 종목 기준)

### 9.3 성능 영향
- FDR API 호출 빈도 증가 → rate limiter로 제어
- DB insert 부하 증가 → upsert 배치 처리로 최적화
- 병렬 처리로 CPU 사용률 증가 → worker 수로 제어

---

## 10. 향후 개선 사항 (v2.0)

1. **재시도 로직 강화**
   - `--retry-failed` 옵션으로 실패 목록만 재수집
   - exponential backoff 재시도 전략

2. **진행상황 저장 (Resume 기능)**
   - 중간에 중단되어도 이어서 실행 가능
   - SQLite로 진행상황 체크포인트 저장

3. **웹 대시보드**
   - 실시간 수집 진행상황 모니터링
   - Flask/FastAPI로 간단한 웹 UI 제공

4. **알림 기능**
   - 수집 완료 시 Slack/Email 알림
   - 실패율 N% 이상 시 경고 알림

5. **데이터 검증**
   - 수집된 데이터의 이상치 탐지
   - 주가 급등락 알림 (전일 대비 ±20% 이상)

---

## 11. 의사결정 필요 사항

### 11.1 구현 범위
- [ ] Phase 1만 먼저 구현? (종목 마스터만)
- [ ] Phase 1-3 전체 한번에 구현?
- [ ] dry-run 모드 포함?
- [ ] Unit test 작성?

### 11.2 성능 튜닝
- [ ] 병렬 워커 수 기본값: 4? 8?
- [ ] Rate limit 기본값: 5 req/sec? 10 req/sec?
- [ ] DB pool_size 증가 필요? (10 → 20?)

### 11.3 에러 처리
- [ ] 실패한 종목은 로그만? 아니면 별도 테이블에 기록?
- [ ] N회 연속 실패 시 자동 중단?

---

## 12. 검토 체크리스트

구현 전 다음 사항을 확인해주세요:

- [ ] FDR API 사용량 제한 확인 (무료 플랜 제한 등)
- [ ] DB 저장 공간 충분한지 확인 (최소 10GB 권장)
- [ ] 병렬 처리 시 메모리 사용량 고려 (워커당 약 200MB)
- [ ] 운영 환경에서 cron 실행 권한 확인
- [ ] 로그 파일 rotation 설정 (logrotate 등)

---

## 13. 승인 및 실행

이 계획을 검토하시고, 다음 중 하나를 선택해주세요:

1. **✅ 승인 - 전체 구현 진행**
   - Phase 1-3 모두 구현
   - 예상 소요 시간: 7-10시간

2. **⚠️ 부분 승인 - Phase 1만 먼저**
   - sync_symbol_master.py만 먼저 구현
   - 예상 소요 시간: 2-3시간

3. **📝 수정 요청**
   - 계획 일부 변경 후 재검토

4. **❌ 보류**
   - 현재 수동 방식 유지
