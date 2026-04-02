# Operations Runbook

## Scope

이 문서는 공용 MySQL 인프라 안의 `real_estate` 전용 DB를 사용하는 운영 절차와 장애 대응 기준을 정의합니다.
공개 전 최종 점검은 `docs/public_release_checklist.md`를 함께 참고합니다.

운영 권장 구조:

- 외부 사용자 요청은 Nginx가 수신
- Flask 앱은 VM 내부 `127.0.0.1:5001`에만 바인딩
- DB bootstrap은 루트 `.env` + `db/compose/mysql-standalone/`에서 수행
- 앱 런타임 연결은 `apps/real-estate-project/.env`의 `RE_DB_*`로 수행

역할 분리:

- 루트 `.env` -> 공용 MySQL bootstrap 계약(`real_estate`, `real_estate_test`, 사용자/권한)
- 앱 `.env` -> real-estate 런타임 접속 정보(`RE_DB_HOST`, `RE_DB_PORT`, `RE_DB_USER`, `RE_DB_PASSWORD`, `RE_DB_NAME`)

## Standard Commands

```bash
cd apps/real-estate-project
set -a && source .env && set +a
python -m src.real_estate.cli validate-config --require-api-key
python -m src.real_estate.cli ingest --lawd-cds 11650 --start-ymd 202401 --end-ymd 202402
python -m src.real_estate.cli clean-anomalies
python -m src.real_estate.cli recalculate-derived
python -m src.real_estate.cli analyze
python -m src.real_estate.cli serve-web --port 5001
```

## Schema Management

전체 테이블 스키마 실행 기준은 `db/init/03_real_estate_schema.sql`입니다.
공용 bootstrap이 첫 볼륨 초기화 시 이 DDL을 적용하고, `init-db`는 기존 DB 재적용/복구 용도로만 사용합니다.
DBA 직접 실행: `mysql -u <user> -p <target_db> < db/init/03_real_estate_schema.sql`

## Phase Gates

1. Config Gate
   - `validate-config --require-api-key` success
2. DB Gate
   - required tables exist
   - missing tables or drift suspected: `init-db` success (또는 `db/init/03_real_estate_schema.sql` 직접 실행)
3. Ingest Gate
   - `rh_trade_analysis` row count > 0
4. Analyze Gate
   - `monthly_dong_analysis` row count > 0
   - `building_transaction_analysis_above_ground` row count > 0
   - optional preprocessing commands completed or intentionally skipped
5. Web Gate
   - `GET /` returns 200
   - `POST /combined_analysis` returns `success: true`

If any gate fails, stop and resolve before proceeding.

## Validation SQL

```sql
SELECT COUNT(*) AS raw_cnt FROM rh_trade_analysis;
SELECT COUNT(*) AS monthly_cnt FROM monthly_dong_analysis;
SELECT COUNT(*) AS above_cnt FROM building_transaction_analysis_above_ground;
SELECT COUNT(*) AS below_cnt FROM building_transaction_analysis_below_ground;
SELECT MIN(CONCAT(dealYear, LPAD(dealMonth,2,'0'))) AS min_ymd,
       MAX(CONCAT(dealYear, LPAD(dealMonth,2,'0'))) AS max_ymd
FROM rh_trade_analysis;
```

## Common Failures

- Missing API key (`RE_API_SERVICE_KEY`)
  - symptom: ingest fails with 401 or validation error
  - action: set valid key in runtime environment (`.env` + source)

- DB connection failure
  - symptom: connection/auth errors in CLI
  - action: verify `RE_DB_*`, network access, account privileges

- Empty analysis output
  - symptom: analysis tables have 0 rows
  - action: check ingest row count and target period, rerun analyze

- Port conflict
  - symptom: web start fails on desired port
  - action: provide another `--port` or rely on auto-search in app entrypoints

## Data Collection Scripts

### 최초 bulk 수집

```bash
bash apps/real-estate-project/scripts/collect_initial.sh
```

- bootstrap이 준비된 DB 기준 2020.01~현재 전체 수집 + 후처리
- 로그: `logs/collect_initial_YYYYMMDD_HHMMSS.log`
- API 제한 시 다음 날 재실행 가능 (중복 방지 내장)

### 일일 정기 수집 (cron)

```bash
# crontab (매일 06:00 KST = 21:00 UTC)
0 21 * * * cd /app/apps/real-estate-project && bash scripts/collect_daily.sh >> logs/cron_collect.log 2>&1
```

- 전월+당월 수집 + 후처리 (개별 단계 실패 시 다음 단계 계속)
- 로그: `logs/collect_daily_YYYYMMDD.log` (7일 자동 보관)
- cron 등록은 VM/system scheduler에서 별도로 관리

### 수집 실패 대응

- 수집 로그 확인: `tail -f logs/collect_daily_$(date +%Y%m%d).log`
- DB 수집 이력 확인: `SELECT * FROM data_ingestion_log ORDER BY created_at DESC LIMIT 20;`
- 특정 구/기간 재수집: `cd apps/real-estate-project && python -m src.real_estate.cli ingest --lawd-cds 11650 --start-ymd 202603 --end-ymd 202603`

## Recovery Steps

1. Re-run config validation
2. Re-run `init-db` (idempotent)
3. Re-run ingest for reduced window (1 region, 2 months)
4. Re-run analyze
5. Re-check API endpoints

## Security Checks

- `pytest -q tests -m "not db"`
- `python -m src.real_estate.cli validate-config --require-api-key`
- `pip-audit -r requirements.txt`
- `pip-audit -r web_ui/requirements.txt`
