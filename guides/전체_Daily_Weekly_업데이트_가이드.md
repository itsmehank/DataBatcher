# 전체 Daily / Weekly 업데이트 가이드

## 개요

DataBatcher의 **일상 운영을 위한 전체 업데이트 스크립트**입니다.

**제공 스크립트**:
- `shell_scripts/daily_kr.sh` — KR 일일 업데이트 (KR 지수 + KR 주식 + KR RS + KR 미너비니)
- `shell_scripts/daily_us.sh` — US 일일 업데이트 (US 지수 + US 주식 + US RS + US 미너비니)
- `shell_scripts/daily_crypto.sh` — Crypto 일일 업데이트 (가격 + 지표)
- `shell_scripts/daily_all.sh` — 통합 실행용 래퍼(위 3개 스크립트를 순서대로 실행)
- `shell_scripts/weekly_all.sh` — 모든 시장의 주간 업데이트 + 종목 마스터 동기화

**대상 시장**: KR 주식, US 주식, Crypto, KR 지수, US 지수

---

## 사전 요구사항

1. **초기 Bulk 수집 완료**: `bash shell_scripts/bulk_all.sh` 실행 완료 상태
2. **Docker MySQL 실행 중**: `cd docker && docker compose up -d`
3. **Python 가상환경 활성화**: `source .venv/bin/activate`

---

## Daily 업데이트 (분리 스크립트 + 통합 래퍼)

### 실행 방법

#### KR 일일 업데이트

```bash
cd /path/to/DataBatcher
bash shell_scripts/daily_kr.sh
```

#### US 일일 업데이트

```bash
cd /path/to/DataBatcher
bash shell_scripts/daily_us.sh
```

#### Crypto 일일 업데이트

```bash
cd /path/to/DataBatcher
bash shell_scripts/daily_crypto.sh
```

#### 통합 실행(호환용)

```bash
cd /path/to/DataBatcher
bash shell_scripts/daily_all.sh
```

### 실행 시각 권장

- **KR만 업데이트**: 평일 17:00 KST (장마감 30분 후)
- **US만 업데이트**: 평일 07:00 KST 다음날 (US 장마감 16:30 ET 후)
- **전체 업데이트 (KR+US+Crypto)**: 평일 07:30 KST 다음날 (모든 시장 마감 후)

### 예상 소요시간

**전체**: 20-40분 (네트워크 상태 및 종목 수에 따라 다름)

| Phase | 소요시간 | 비고 |
|-------|----------|------|
| Phase 0 (지수 일봉) | 2-3분 | KR 지수 2개 + US 지수 3개 |
| Phase 1 (주식+Crypto 일봉) | 15-30분 | KR ~2,900개 + US ~8,000개 + Crypto 활성 심볼 |
| Phase 2 (RS 지표) | 2-5분 | 최근 7일 RS 계산 |
| Phase 3 (미너비니 스크리닝) | 1-2분 | 최근 7일 스크리닝 |

### 실행 순서 및 각 단계 설명

`daily_all.sh`는 아래 3개 스크립트를 순서대로 호출합니다.

1. `daily_kr.sh`
2. `daily_us.sh`
3. `daily_crypto.sh`

각 분리 스크립트는 내부 단계에서 일부 실패가 있어도 다음 단계를 계속 진행하며, 최종 요약에서 실패 건수를 출력합니다.

> **순서 원칙**: 지수(Index)를 먼저 수집한 후 주식(Stock)을 수집합니다.
> RS 지표 계산이 벤치마크 지수 데이터(KOSPI 1001, US500)에 의존하기 때문입니다.

#### Phase 0: 지수 일봉 (Index Daily)

| 단계 | 명령어 | 설명 | 기본 수집 기간 |
|------|--------|------|----------------|
| 0-1 | `python scripts/kr_index_daily_update.py --all --force` | KR 지수 일봉 업데이트 | 최근 50일 |
| 0-2 | `python scripts/us_index_daily_update.py --all --force` | US 지수 일봉 업데이트 | 최근 50일 |

#### Phase 1: 주식 + Crypto 일봉 (Stock/Crypto Daily)

| 단계 | 명령어 | 설명 | 기본 수집 기간 |
|------|--------|------|----------------|
| 1-1 | `python scripts/daily_update.py --all --force` | KR 주식 일봉 업데이트 | 최근 30일 |
| 1-2 | `python scripts/us_daily_update.py --all --with-indicators --force` | US 주식 일봉 + 지표 업데이트 | 최근 50일 |
| 1-3 | `python scripts/crypto_daily_update.py --all --with-indicators` | Crypto 일봉 + 지표 업데이트 | 최근 30일 |

**참고**: `crypto_daily_update.py`는 `--force` 옵션이 없으므로 생략.

#### Phase 2: RS 지표 (RS Indicators)

| 단계 | 명령어 | 설명 | 기본 계산 일수 |
|------|--------|------|----------------|
| 2-1 | `python scripts/kr_rs_update.py --days 7 --force` | KR RS Rating/Line/Blue Dot 계산 | 최근 7일 |
| 2-2 | `python scripts/us_rs_update.py --days 7 --force` | US RS Rating/Line/Blue Dot 계산 | 최근 7일 |

**참고**: RS 지표는 주식+지수 데이터가 모두 필요하므로 Phase 1 이후 실행.

#### Phase 3: Minervini 스크리닝 (Minervini Screening)

| 단계 | 명령어 | 설명 | 기본 계산 일수 |
|------|--------|------|----------------|
| 3-1 | `python scripts/kr_minervini_update.py --days 7 --force` | KR 미너비니 트렌드 템플릿 스크리닝 | 최근 7일 |
| 3-2 | `python scripts/us_minervini_update.py --days 7 --force` | US 미너비니 트렌드 템플릿 스크리닝 | 최근 7일 |

**참고**: 미너비니 스크리닝은 RS 지표를 사용하므로 Phase 2 이후 실행.

### --force 옵션 사용 이유

모든 스크립트에 `--force` 옵션을 사용하여 **장마감 시각 체크를 건너뜁니다**.

- **이유**: Cron이 적절한 시간에 호출한다고 가정하므로 스크립트 내부 체크 불필요
- **주의**: Cron 설정 시 실제 장마감 시각을 고려하여 시간 설정 필요
  - KR: 평일 15:30 마감 + 30분 버퍼 = 16:00 이후 실행
  - US: 평일 16:00 ET 마감 + 30분 버퍼 = 16:30 ET (다음날 06:30 KST) 이후 실행

---

## Weekly 업데이트 (weekly_all.sh)

### 실행 방법

```bash
cd /path/to/DataBatcher
bash shell_scripts/weekly_all.sh
```

### 실행 시각 권장

- **토요일 오전** 권장 (예: 토요일 10:00 KST)
- 평일 실행 시 최신(불완전) 주는 자동 제외됨

### 예상 소요시간

**전체**: 30-60분 (종목 마스터 동기화 포함, yfinance sector 수집 시 ~1시간)

| Phase | 소요시간 | 비고 |
|-------|----------|------|
| Phase 0 (종목 마스터 동기화) | 5-60분 | US 종목 마스터에서 yfinance sector 수집 시 ~1시간 |
| Phase 1 (지수 주봉) | 1-2분 | KR 지수 2개 + US 지수 3개 |
| Phase 2 (주식 주봉) | 10-20분 | KR ~2,900개 + US ~8,000개 |
| Phase 3 (Crypto 주봉) | 5-10분 | 활성 심볼 |

### 실행 순서 및 각 단계 설명

#### Phase 0: 종목 마스터 동기화 (Symbol Master Sync)

| 단계 | 명령어 | 설명 | 비고 |
|------|--------|------|------|
| 0-1 | `python scripts/sync_symbol_master.py` | KR 주식 종목 마스터 동기화 | 신규/폐지 종목 감지 |
| 0-2 | `python scripts/us_sync_symbol_master.py` | US 주식 종목 마스터 동기화 | yfinance sector 수집 포함 (~1시간) |
| 0-3 | `python scripts/crypto_sync_symbol_master.py --all` | Crypto 심볼 마스터 동기화 | 신규 거래쌍 감지 |
| 0-4 | `python scripts/kr_index_sync_master.py` | KR 지수 마스터 동기화 | KOSPI, KOSDAQ |
| 0-5 | `python scripts/us_index_sync_master.py` | US 지수 마스터 동기화 | S&P 500, DJI, IXIC |

**참고**: 0-2 단계(US 종목 마스터)에서 신규 종목의 sector/industry를 yfinance API로 수집합니다.
이미 sector가 채워진 종목은 건너뛰므로 재실행 시 시간이 단축됩니다.

#### Phase 1: 지수 주봉 (Index Weekly)

| 단계 | 명령어 | 설명 | 데이터 소스 |
|------|--------|------|-------------|
| 1-1 | `python scripts/kr_index_weekly_update.py --all` | KR 지수 주봉 업데이트 | kr_index_prices 일봉 → 주봉 집계 |
| 1-2 | `python scripts/us_index_weekly_update.py --all` | US 지수 주봉 업데이트 | us_index_prices 일봉 → 주봉 집계 |

**참고**: `kr_index_weekly_update.py`는 실행 요일 기준으로 최신 주 포함 여부(`skip_latest_week`)를 자동 판단합니다.

#### Phase 2: 주식 주봉 (Stock Weekly)

| 단계 | 명령어 | 설명 | 데이터 소스 |
|------|--------|------|-------------|
| 2-1 | `python scripts/weekly_update.py --all` | KR 주식 주봉 업데이트 | stock_prices 일봉 → 주봉 집계 |
| 2-2 | `python scripts/us_weekly_update.py --all` | US 주식 주봉 업데이트 | us_stock_prices 일봉 → 주봉 집계 |

#### Phase 3: Crypto 주봉 (Crypto Weekly)

| 단계 | 명령어 | 설명 | 데이터 소스 |
|------|--------|------|-------------|
| 3-1 | `python scripts/crypto_weekly_update.py --all --with-indicators` | Crypto 주봉 + 지표 업데이트 | crypto_prices_daily → 주봉 집계 |

### 주말/평일 실행 차이

- **토요일/일요일 실행**: 최신 주(금요일 마감 주)까지 포함
- **평일 실행**: 최신 주는 불완전하므로 자동 제외 (`skip_latest_week` 동작)
- **로직**: `aggregate_daily_to_weekly_trading_days()` 함수에서 현재 요일 기준으로 자동 판단

---

## Cron 자동화 설정 예시

### Linux/Mac Crontab

```bash
# crontab 편집
crontab -e

# 추가할 내용:

# --- Daily 업데이트 (전체 시장, 다음날 오전 07:30 KST) ---
30 7 * * 2-6 cd /path/to/DataBatcher && source .venv/bin/activate && bash shell_scripts/daily_all.sh >> logs/daily_all.log 2>&1

# --- KR만 Daily 업데이트 (평일 17:00 KST) ---
# 0 17 * * 1-5 cd /path/to/DataBatcher && source .venv/bin/activate && python scripts/kr_index_daily_update.py --all --force && python scripts/daily_update.py --all --force && python scripts/kr_rs_update.py --days 7 --force && python scripts/kr_minervini_update.py --days 7 --force >> logs/daily_kr.log 2>&1

# --- US만 Daily 업데이트 (다음날 오전 07:00 KST) ---
# 0 7 * * 2-6 cd /path/to/DataBatcher && source .venv/bin/activate && python scripts/us_index_daily_update.py --all --force && python scripts/us_daily_update.py --all --with-indicators --force && python scripts/us_rs_update.py --days 7 --force && python scripts/us_minervini_update.py --days 7 --force >> logs/daily_us.log 2>&1

# --- Weekly 업데이트 (토요일 오전 10:00 KST) ---
0 10 * * 6 cd /path/to/DataBatcher && source .venv/bin/activate && bash shell_scripts/weekly_all.sh >> logs/weekly_all.log 2>&1
```

**참고**:
- `2-6`은 화요일~토요일 (월요일 밤 미국 장마감 데이터를 화요일 아침 수집)
- `1-5`는 월요일~금요일 (한국 장마감 당일 수집)

### Windows Task Scheduler

1. **작업 스케줄러 실행** (taskschd.msc)
2. **기본 작업 만들기** 선택
3. **트리거**: "매일" 또는 "매주"
4. **동작**: "프로그램 시작"
   - 프로그램: `C:\Windows\System32\bash.exe`
   - 인수: `shell_scripts/daily_all.sh`
   - 시작 위치: `C:\path\to\DataBatcher`
5. **조건**: "컴퓨터의 전원이 AC 전원에 연결되어 있을 때만 작업 시작" 체크 해제
6. **설정**: "작업이 실패한 경우 다시 시작 간격" 설정 (선택 사항)

---

## 부분 실행 (개별 스크립트 호출)

특정 시장만 업데이트하려면 개별 스크립트를 직접 호출하세요.

### KR만 Daily 업데이트

```bash
python scripts/kr_index_daily_update.py --all --force
python scripts/daily_update.py --all --force
python scripts/kr_rs_update.py --days 7 --force
python scripts/kr_minervini_update.py --days 7 --force
```

### US만 Daily 업데이트

```bash
python scripts/us_index_daily_update.py --all --force
python scripts/us_daily_update.py --all --with-indicators --force
python scripts/us_rs_update.py --days 7 --force
python scripts/us_minervini_update.py --days 7 --force
```

### Crypto만 Daily 업데이트

```bash
python scripts/crypto_daily_update.py --all --with-indicators
```

### 특정 마켓만 업데이트

```bash
# KOSPI만
python scripts/daily_update.py --all --market KOSPI --force

# NASDAQ만
python scripts/us_daily_update.py --all --market NASDAQ --with-indicators --force
```

---

## 수집 결과 확인

### Daily 업데이트 확인

```sql
-- 최신 업데이트 일자 확인
SELECT 'KR 주식' as market, MAX(date) as latest FROM stock_prices
UNION ALL
SELECT 'US 주식', MAX(date) FROM us_stock_prices
UNION ALL
SELECT 'Crypto', MAX(date) FROM crypto_prices_daily
UNION ALL
SELECT 'KR 지수', MAX(date) FROM kr_index_prices
UNION ALL
SELECT 'US 지수', MAX(date) FROM us_index_prices;

-- 어제 날짜 기준 수집 종목 수
SELECT 'KR 주식' as market, COUNT(DISTINCT symbol) as symbols FROM stock_prices WHERE date = '2025-01-19'
UNION ALL
SELECT 'US 주식', COUNT(DISTINCT symbol) FROM us_stock_prices WHERE date = '2025-01-19'
UNION ALL
SELECT 'Crypto', COUNT(DISTINCT symbol) FROM crypto_prices_daily WHERE date = '2025-01-19';

-- RS 지표 최신 일자 확인
SELECT 'KR RS', indicator, MAX(date) as latest, COUNT(*) as rows FROM stock_indicators WHERE indicator IN ('ibd_rs_rating', 'rs_line', 'blue_dot') GROUP BY indicator
UNION ALL
SELECT 'US RS', indicator, MAX(date), COUNT(*) FROM us_stock_indicators WHERE indicator IN ('ibd_rs_rating', 'rs_line', 'blue_dot') GROUP BY indicator;

-- 미너비니 스크리닝 최신 결과
SELECT 'KR 미너비니' as market, MAX(screen_date) as latest, COUNT(*) as passed FROM minervini_screen_results_kr
UNION ALL
SELECT 'US 미너비니', MAX(screen_date), COUNT(*) FROM minervini_screen_results_us;
```

### Weekly 업데이트 확인

```sql
-- 최신 주봉 일자 확인
SELECT 'KR 주식 주봉' as market, MAX(week_start) as latest FROM stock_prices_weekly
UNION ALL
SELECT 'US 주식 주봉', MAX(week_start) FROM us_stock_prices_weekly
UNION ALL
SELECT 'Crypto 주봉', MAX(week_start) FROM crypto_prices_weekly
UNION ALL
SELECT 'KR 지수 주봉', MAX(week_start) FROM kr_index_prices_weekly
UNION ALL
SELECT 'US 지수 주봉', MAX(week_start) FROM us_index_prices_weekly;

-- 종목 마스터 최신 동기화 확인
SELECT 'KR 주식' as market, status, COUNT(*) as cnt FROM symbol_master GROUP BY status
UNION ALL
SELECT 'US 주식', status, COUNT(*) FROM us_symbol_master GROUP BY status
UNION ALL
SELECT 'Crypto', status, COUNT(*) FROM crypto_symbol_master GROUP BY status;
```

---

## 트러블슈팅

### 부분 실패

- 스크립트는 개별 단계가 실패해도 다음 단계를 계속 진행합니다.
- 최종 결과에서 **성공/실패 횟수**를 확인하세요.
- 실패한 종목은 `logs/` 디렉토리의 `*_failed.log` 파일에서 확인 가능합니다.

### 재실행 안전성

- **Daily 업데이트**: INSERT ONLY 모드이므로 기존 데이터 보존 (안전한 재실행 가능)
- **Weekly 업데이트**: 주봉 집계는 INSERT ONLY 모드이므로 기존 데이터 보존
- 실패 후 재실행하면 누락된 데이터만 추가됩니다.

### RS 지표 실패: "벤치마크 지수 데이터 없음"

- RS 지표(kr_rs_update, us_rs_update)는 벤치마크 지수 데이터가 필요합니다.
- **KR**: `kr_index_prices` 테이블에 KOSPI(1001) 데이터가 있어야 합니다.
- **US**: `us_index_prices` 테이블에 S&P 500(US500) 데이터가 있어야 합니다.
- **해결**: 지수 수집(Phase 0)이 정상 완료되었는지 확인하세요.

### 미너비니 스크리닝 실패: "RS Rating 데이터 없음"

- 미너비니 스크리닝은 RS Rating/Blue Dot 지표를 사용합니다.
- **해결**: RS 지표(Phase 2)가 정상 완료되었는지 확인하세요.

### US 종목 마스터 동기화가 너무 오래 걸림

- `us_sync_symbol_master.py`는 yfinance API로 sector/industry를 수집합니다.
- 신규 종목이 많으면 ~1시간 소요될 수 있습니다.
- **빠른 실행**: `--skip-yfinance` 옵션으로 sector 수집 건너뛰기
  ```bash
  python scripts/us_sync_symbol_master.py --skip-yfinance
  ```
- **부분 실행**: `--yfinance-limit 100` 옵션으로 상위 100개만 수집
  ```bash
  python scripts/us_sync_symbol_master.py --yfinance-limit 100
  ```

### Rate Limiting

- KR/US 주식 수집 시 FDR API rate limit에 의해 속도가 제한됩니다.
- `config/settings.yaml`의 `runtime.rate_limit_per_sec` 값으로 조절 가능합니다.
- Daily 업데이트는 최근 30-50일만 수집하므로 bulk 수집보다 빠릅니다.

### Cron 로그 확인

```bash
# 최근 실행 로그 확인
tail -f logs/daily_all.log
tail -f logs/weekly_all.log

# 전체 로그 확인
less logs/daily_all.log
less logs/weekly_all.log
```

### 스크립트 실행 권한 오류

```bash
# 실행 권한 부여
chmod +x shell_scripts/daily_all.sh
chmod +x shell_scripts/weekly_all.sh
```

---

## 참고 문서

- **초기 Bulk 수집**: `guides/전체_Bulk_수집_가이드.md`
- **한국 주식 일봉**: `guides/한국주식_일봉_가이드.md`
- **미국 주식 일봉**: `guides/미국주식_일봉_가이드.md`
- **미너비니 스크리닝**: `guides/미너비니_트렌드_템플릿_가이드.md`
- **데이터베이스 스키마**: `docs/database_schema.md`
