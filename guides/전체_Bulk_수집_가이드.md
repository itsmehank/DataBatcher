# 전체 Bulk 수집 가이드

## 개요

`apps/ingest-databatcher/ops/shell/bulk_all.sh`는 DataBatcher의 **모든 시장 데이터를 한 번에 수집**하는 셸 스크립트입니다.

**대상 시장**: KR 주식, US 주식, Crypto, KR 지수, US 지수
**수집 기간**: KR/US = 2020-01-01 ~ 어제, Crypto = 2017-01-01 ~ 어제

---

## 사전 요구사항

1. **Docker MySQL 실행 중**: `cd docker && docker compose up -d`
2. **DB 스키마 초기화**: `python scripts/init_db.py`
3. **Python 가상환경 활성화**: `source .venv/bin/activate`
4. **의존성 설치**: `pip install -r requirements.txt`

---

## 실행 방법

```bash
cd /path/to/DataBatcher
bash apps/ingest-databatcher/ops/shell/bulk_all.sh
```

---

## 실행 순서 및 예상 소요시간

> **순서 원칙**: 지수(Index)를 먼저 수집한 후 주식(Stock)을 수집합니다.
> RS 지표 계산(kr_rs_update, us_rs_update)이 벤치마크 지수 데이터(KOSPI 1001, US500)에 의존하기 때문입니다.

### Phase 0: 종목 마스터 동기화 (~1시간)

> **참고**: US 종목 마스터 동기화(0-2)에서 yfinance sector 수집이 포함되어 ~1시간 소요됩니다.
> 이후 재실행 시에는 신규 종목만 처리하므로 시간이 크게 단축됩니다.

| 단계 | 설명 |
|------|------|
| 0-1 | KR 주식 종목 마스터 동기화 |
| 0-2 | US 주식 종목 마스터 동기화 |
| 0-3 | Crypto 심볼 마스터 동기화 |
| 0-4 | KR 지수 마스터 동기화 |
| 0-5 | US 지수 마스터 동기화 |

### Phase 1: 한국 지수 (~2-3분)

| 단계 | 설명 |
|------|------|
| 1-1 | KR 지수 일봉 bulk (2020~어제) |
| 1-2 | KR 지수 주봉 bulk (DB 전체 기간 자동) |

### Phase 2: 미국 지수 (~2-3분)

| 단계 | 설명 |
|------|------|
| 2-1 | US 지수 일봉 bulk (2020~어제) |
| 2-2 | US 지수 주봉 bulk (DB 전체 기간 자동) |

### Phase 3: 한국 주식 (~20-30분)

| 단계 | 설명 |
|------|------|
| 3-1 | KR 주식 일봉 bulk (2020~어제, workers=4) |
| 3-2 | KR 주식 주봉 bulk (DB 전체 기간 자동) |
| 3-3 | KR RS 지표 계산 (전체 기간) |

### Phase 4: 미국 주식 (~30-60분)

| 단계 | 설명 |
|------|------|
| 4-1 | US 주식 일봉 bulk + 지표 (2020~어제, workers=4) |
| 4-2 | US 주식 주봉 bulk (DB 전체 기간 자동) |
| 4-3 | US RS 지표 계산 (전체 기간) |

### Phase 5: 크립토 (~5-10분)

| 단계 | 설명 |
|------|------|
| 5-1 | Crypto 일봉 bulk + 지표 (2017~어제) |
| 5-2 | Crypto 주봉 bulk + 지표 (2017~어제) |

**전체 예상 소요시간**: 약 2~3시간 (yfinance sector 수집 + 네트워크 상태에 따라 다름)

---

## 경량 테스트 실행

전체 파이프라인이 정상 동작하는지 **최소 데이터로 빠르게 검증**하려면 테스트 스크립트를 사용하세요.

```bash
cd /path/to/DataBatcher
bash apps/ingest-databatcher/ops/shell/bulk_all_test.sh
```

### 본 실행과 비교

| 항목 | `bulk_all.sh` (본 실행) | `bulk_all_test.sh` (테스트) |
|------|------------------------|-----------------------------|
| 수집 기간 | 2020-01-01 ~ 어제 (5년) | **최근 3개월** |
| KR 주식 | 전체 (~2,900개) | **시총 상위 3개** |
| US 주식 | 전체 (~8,000개) | **시총 상위 3개** |
| Crypto | 전체 ACTIVE 심볼 | **BTCUSDT, ETHUSDT** |
| KR 지수 | 전체 (KOSPI+KOSDAQ) | **KOSPI만** |
| US 지수 | 전체 (3개) | **SP500만** |
| RS 지표 | 전체 일수 (9999일) | **최근 5일** |
| workers | 4 | 2 |
| 예상 소요시간 | 1~2시간 | **3~5분** |

### 테스트 스크립트 실행 순서

Phase 순서와 로직은 본 실행(`bulk_all.sh`)과 **완전히 동일**합니다.
차이는 각 스크립트에 `--top`, `--symbols`, `--market`, `--days` 옵션으로 데이터 범위만 제한한 것입니다.

| Phase | 단계 | 내용 | 제한 옵션 |
|-------|------|------|-----------|
| 0 | 0-1~0-5 | 마스터 동기화 | crypto `--symbols`, US `--skip-yfinance` |
| 1 | 1-1~1-2 | KR 지수 | `--market KOSPI` |
| 2 | 2-1~2-2 | US 지수 | `--market SP500` |
| 3 | 3-1~3-3 | KR 주식 + RS | `--top 3`, `--days 5` |
| 4 | 4-1~4-3 | US 주식 + RS | `--top 3`, `--days 5` |
| 5 | 5-1~5-2 | Crypto | `--symbols BTCUSDT ETHUSDT` |

### 활용 시나리오

- **초기 환경 세팅 후**: DB 초기화 → 테스트 스크립트로 전체 파이프라인 검증 → 본 실행
- **코드 수정 후**: 변경 사항이 전체 흐름에 영향을 주는지 빠르게 확인
- **새 서버 배포 시**: 환경 설정, DB 연결, API 접근이 모두 정상인지 검증

---

## 부분 실행

특정 Phase만 실행하려면 개별 스크립트를 직접 호출하세요.

```bash
# 예시: US 주식만 수집 (yfinance sector 포함)
python scripts/us_sync_symbol_master.py
python scripts/us_bulk_update.py --start 2020-01-01 --end 2025-12-31 --workers 4 --with-indicators
python scripts/us_bulk_update_weekly.py
python scripts/us_rs_update.py --days 9999 --force

# 예시: US 주식만 수집 (yfinance sector 스킵, 빠른 실행)
python scripts/us_sync_symbol_master.py --skip-yfinance
python scripts/us_bulk_update.py --start 2020-01-01 --end 2025-12-31 --workers 4 --with-indicators
python scripts/us_bulk_update_weekly.py
python scripts/us_rs_update.py --days 9999 --force
```

---

## 수집 결과 확인

```sql
-- KR 주식
SELECT COUNT(DISTINCT symbol) as symbols, COUNT(*) as rows, MIN(date) as oldest, MAX(date) as newest FROM stock_prices;
SELECT indicator, COUNT(*) as rows FROM stock_indicators GROUP BY indicator;

-- US 주식
SELECT COUNT(DISTINCT symbol) as symbols, COUNT(*) as rows, MIN(date) as oldest, MAX(date) as newest FROM us_stock_prices;

-- Crypto
SELECT COUNT(DISTINCT symbol) as symbols, COUNT(*) as rows, MIN(date) as oldest, MAX(date) as newest FROM crypto_prices_daily;

-- KR 지수
SELECT COUNT(DISTINCT symbol) as symbols, COUNT(*) as rows, MIN(date) as oldest, MAX(date) as newest FROM kr_index_prices;

-- US 지수
SELECT COUNT(DISTINCT symbol) as symbols, COUNT(*) as rows, MIN(date) as oldest, MAX(date) as newest FROM us_index_prices;
```

---

## 트러블슈팅

### 부분 실패
- 스크립트는 개별 단계가 실패해도 다음 단계를 계속 진행합니다.
- 최종 결과에서 실패 횟수를 확인하세요.
- 실패한 종목은 `logs/` 디렉토리의 `*_failed.log` 파일에서 확인 가능합니다.

### 재실행 안전성
- INSERT ONLY 모드이므로 기존 데이터는 보존됩니다.
- 동일한 스크립트를 다시 실행해도 기존 데이터가 덮어씌워지지 않습니다.
- 실패 후 재실행하면 누락된 데이터만 추가됩니다.

### RS 지표 실패: "벤치마크 지수 데이터 없음"
- RS 지표(kr_rs_update, us_rs_update)는 벤치마크 지수 데이터가 필요합니다.
- KR: `kr_index_prices` 테이블에 KOSPI(1001) 데이터가 있어야 합니다.
- US: `us_index_prices` 테이블에 S&P 500(US500) 데이터가 있어야 합니다.
- **해결**: 지수 수집(Phase 1, 2)이 정상 완료되었는지 확인하세요.

### Rate Limiting
- KR/US 주식 수집 시 FDR API rate limit에 의해 속도가 제한됩니다.
- `config/settings.yaml`의 `runtime.rate_limit_per_sec` 값으로 조절 가능합니다.
- workers 수가 많을수록 빠르지만, rate limit 초과 위험이 있습니다 (기본값 4 권장).