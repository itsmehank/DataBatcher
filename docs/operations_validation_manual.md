# 운영 검증 수동 가이드

이 문서는 스케줄 등록 여부와 관계없이, 운영자가 필요할 때 수동으로 실행하는 검증 절차를 정의합니다.

## 1) 언제 수행하나
- 새 PC/서버에 초기 세팅 후
- Python 경로, DB 연결정보, 스케줄러 환경변수 변경 후
- 장애 복구 후 정상화 확인이 필요할 때

## 2) 사전 확인
1. `apps/ingest-databatcher/ops/scheduler/windows/scheduler.env`에 아래 키가 있는지 확인
   - `BATCH_PYTHON_EXE`
   - `SCHEDULER_PYTHON_EXE` (선택)
   - `GIT_BASH_EXE`
   - `APPRISE_URLS`
2. 배치 파이썬으로 의존성 설치
   - `"<BATCH_PYTHON_EXE>" -m pip install -r requirements.txt`
3. DB 타겟 확인
   - `DATABASE_URL`(최우선) 또는 `config/settings.dev.yaml` 값 점검

## 3) 수동 실행 검증
아래 명령은 프로젝트 루트에서 실행합니다.

```powershell
powershell -ExecutionPolicy Bypass -File .\apps\ingest-databatcher\ops\scheduler\windows\run_daily.ps1 -Target KR
powershell -ExecutionPolicy Bypass -File .\apps\ingest-databatcher\ops\scheduler\windows\run_daily.ps1 -Target US
powershell -ExecutionPolicy Bypass -File .\apps\ingest-databatcher\ops\scheduler\windows\run_weekly.ps1
powershell -ExecutionPolicy Bypass -File .\apps\ingest-databatcher\ops\scheduler\windows\cleanup_logs.ps1
```

## 4) 로그/알림 확인
- 로그 파일
  - `logs/scheduler/daily_kr_*.log`
  - `logs/scheduler/daily_us_*.log`
  - `logs/scheduler/weekly_*.log`
  - `logs/scheduler/cleanup_*.log`
- 각 로그에서 아래 문자열 확인
  - `DB healthcheck start`
  - `DB connection OK`
  - `completed successfully`
- Apprise 알림 채널에서 SUCCESS/FAILED 수신 확인

## 5) 데이터 검증 SQL
참고: 현재 스케줄러 daily 대상은 KR/US이며, Crypto daily는 제외되어 있습니다.

Daily 최신성 확인:

```sql
SELECT 'KR 주식' as market, MAX(date) as latest FROM stock_prices
UNION ALL
SELECT 'US 주식', MAX(date) FROM us_stock_prices
UNION ALL
SELECT 'KR 지수', MAX(date) FROM kr_index_prices
UNION ALL
SELECT 'US 지수', MAX(date) FROM us_index_prices;
```

Weekly 최신성 확인:

```sql
SELECT 'KR 주식 주봉' as market, MAX(week_start) as latest FROM stock_prices_weekly
UNION ALL
SELECT 'US 주식 주봉', MAX(week_start) FROM us_stock_prices_weekly
UNION ALL
SELECT 'Crypto 주봉', MAX(week_start) FROM crypto_prices_weekly
UNION ALL
SELECT 'KR 지수 주봉', MAX(week_start) FROM kr_index_prices_weekly
UNION ALL
SELECT 'US 지수 주봉', MAX(week_start) FROM us_index_prices_weekly;
```

## 6) PASS / FAIL 기준
- PASS
  - 각 실행 종료코드 0
  - 스케줄러 로그 파일 생성
  - 로그 내 DB healthcheck 성공
  - 데이터 최신성 SQL 결과가 기대 범위 충족
- FAIL
  - 종료코드 non-zero
  - 로그 미생성 또는 DB healthcheck 실패
  - 알림 미수신(알림 필수 운영 정책일 때)

## 7) 실패 시 1차 조치
1. `BATCH_PYTHON_EXE` 경로와 실행 권한 확인
2. `"<BATCH_PYTHON_EXE>" -m pip install -r requirements.txt` 재실행
3. `DATABASE_URL`/`config/settings.dev.yaml` 값 재점검
4. DB 접속 가능 여부(방화벽, 계정, 포트) 확인
5. 동일 명령 재실행 후 로그 비교
