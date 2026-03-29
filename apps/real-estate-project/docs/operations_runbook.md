# Operations Runbook

## Scope

이 문서는 외부 MySQL을 사용하는 RealEstateProject 운영 절차와 장애 대응 기준을 정의합니다.
공개 전 최종 점검은 `docs/public_release_checklist.md`를 함께 참고합니다.

운영 권장 구조:

- 외부 사용자 요청은 Nginx가 수신
- Flask 앱은 VM 내부 `127.0.0.1:5001`에만 바인딩
- GitHub Actions 배포 시 `VM_SSH_KNOWN_HOSTS` secret으로 SSH 호스트 검증 수행

## Standard Commands

```bash
cd apps/real-estate-project
python -m src.real_estate.cli validate-config --require-api-key
python -m src.real_estate.cli init-db
python -m src.real_estate.cli ingest --lawd-cds 11650 --start-ymd 202401 --end-ymd 202402
python -m src.real_estate.cli clean-anomalies
python -m src.real_estate.cli recalculate-derived
python -m src.real_estate.cli analyze
python -m src.real_estate.cli serve-web --port 5001
```

## Schema Management

전체 테이블 스키마는 `sql/init_schema.sql`에 단일 정의(SSOT).
`init-db` 또는 각 모듈의 `setup_database()` 실행 시 `project_config.ensure_schema()`가 이 SQL을 실행합니다.
DBA 직접 실행: `mysql -u <user> -p real_estate < sql/init_schema.sql`

## Phase Gates

1. Config Gate
   - `validate-config --require-api-key` success
2. DB Gate
   - `init-db` success (또는 `sql/init_schema.sql` 직접 실행)
   - required tables exist
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

- DB 초기화 + 2020.01~현재 전체 수집 + 후처리
- 로그: `logs/collect_initial_YYYYMMDD_HHMMSS.log`
- API 제한 시 다음 날 재실행 가능 (중복 방지 내장)

### 일일 정기 수집 (cron)

```bash
# crontab (매일 06:00 KST = 21:00 UTC)
0 21 * * * cd /app/apps/real-estate-project && bash scripts/collect_daily.sh >> logs/cron_collect.log 2>&1
```

- 전월+당월 수집 + 후처리 (개별 단계 실패 시 다음 단계 계속)
- 로그: `logs/collect_daily_YYYYMMDD.log` (7일 자동 보관)
- 모노레포 배포 시 루트 `.github/workflows/`에서 동일 cron 등록 로직 구성 필요

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
