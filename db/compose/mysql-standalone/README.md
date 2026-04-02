# MySQL Standalone (Docker Compose)

This directory is a standalone MySQL project extracted from the original Grafana + MySQL setup.

## Files

- `docker-compose-mysql.yaml`: MySQL-only Docker Compose file
- `../.env.example`: Root environment template (single source of truth)
- `mysql/my.cnf`: MySQL server configuration
- `mysql/init/setup.sh`: Extra bootstrap for `${MYSQL_DATABASE}_test`, `real_estate`, `real_estate_test` grants
- `../db/init/01_schema.sql`: DataBatcher main schema (mounted into init dir)
- `../db/init/03_real_estate_schema.sql`: RealEstateProject schema (mounted for bootstrap reuse)

## Quick Start

1. Prepare root env file (single source of truth).
   Run this command from project root:

   ```bash
   cp .env.example .env
   ```

2. Update values in root `.env` (at minimum `MYSQL_ROOT_PASSWORD`, `MYSQL_PASSWORD`, `DATABASE_URL`, `REAL_ESTATE_*`).

   Keep these values aligned:
   - `MYSQL_DATABASE` == database name in `DATABASE_URL`
   - `MYSQL_PORT` == port in `DATABASE_URL`
   - `REAL_ESTATE_DB_NAME` / `REAL_ESTATE_TEST_DB_NAME` are the dedicated DBs for `apps/real-estate-project`

   Default monorepo contract:
   - DataBatcher / trading-view bootstrap DB: `trade`
   - real-estate bootstrap DBs: `real_estate`, `real_estate_test`

3. Start MySQL from project root:

   ```bash
   docker compose -f db/compose/mysql-standalone/docker-compose-mysql.yaml --env-file .env up -d
   ```

   If port `3306` is already in use, you can run temporary port override:

   ```bash
   MYSQL_PORT=3307 docker compose -f db/compose/mysql-standalone/docker-compose-mysql.yaml --env-file .env up -d
   ```

   In that case, update `DATABASE_URL` port to `3307` too if app scripts should target this MySQL.

4. Check status:

   ```bash
   docker compose -f db/compose/mysql-standalone/docker-compose-mysql.yaml --env-file .env ps
   ```

5. View logs:

   ```bash
   docker compose -f db/compose/mysql-standalone/docker-compose-mysql.yaml --env-file .env logs -f mysql
   ```

6. Stop service:

   ```bash
   docker compose -f db/compose/mysql-standalone/docker-compose-mysql.yaml --env-file .env down
   ```

## Notes

- Data is persisted in the named volume `mysql_data`.
- This compose and DataBatcher scripts share the same root `.env` values.
- Root `.env` is the bootstrap contract only. Runtime apps use their own env files:
  - `apps/trading-view-project/backend/.env` -> `DATABASE_URL` for trading-view runtime
  - `apps/real-estate-project/.env` -> `RE_DB_*` for real-estate runtime
- Init scripts run only on first initialization (when volume is empty):
  - `01_schema.sql` creates DataBatcher tables/views.
  - `02_auth_schema.sql` creates the trading-view auth table.
  - `03_real_estate_schema.sql` provides the real-estate table DDL.
  - `setup.sh` creates `${MYSQL_DATABASE}_test`, `REAL_ESTATE_DB_NAME`, `REAL_ESTATE_TEST_DB_NAME` and grants the configured users.
- Auth still uses `MYSQL_*` credentials from root `.env` (password-based login).
- `apps/real-estate-project` runtime uses its own `.env` for `RE_DB_*`; root `.env` is the bootstrap contract, not the app runtime secret store.
- If schema changes after first init, re-apply the relevant init path or reset volume.
- To fully reset data, run:

  ```bash
  docker compose -f db/compose/mysql-standalone/docker-compose-mysql.yaml --env-file .env down -v
  ```

## Backup / Restore

백업/복구 스크립트는 프로젝트 루트 `apps/ingest-databatcher/ops/shell/` 아래에 있습니다.

- 월간 full 백업 생성(성공 시 이전 백업 자동 삭제, 최신 1개만 유지):

  ```bash
  bash apps/ingest-databatcher/ops/shell/db_backup_monthly.sh
  ```

  - 출력 경로: `backups/mysql/monthly/`
  - 파일 형식: `.sql.zst` (zstd 미설치 시 `.sql.gz`)
  - 기본 출력: `${MYSQL_DATABASE}`와 `${REAL_ESTATE_DB_NAME}` 각각 1개씩

- 복구(대상 MySQL 컨테이너는 먼저 수동 기동):

  ```bash
  docker compose -f db/compose/mysql-standalone/docker-compose-mysql.yaml --env-file .env up -d
  bash apps/ingest-databatcher/ops/shell/db_restore_full.sh --file backups/mysql/monthly/<backup_file>
  ```

- 대상 DB를 재생성 후 복구하려면:

  ```bash
  bash apps/ingest-databatcher/ops/shell/db_restore_full.sh --file backups/mysql/monthly/<backup_file> --target-db trade --recreate-db --yes
  ```

## Scheduling

별도 스케줄러 스크립트 없이, `db_backup_monthly.sh`를 cron에 등록해 월 1회 실행하는 방식 권장:

```bash
30 3 1 * * cd /Users/hank.es/PythonProject/DataBatcher && bash apps/ingest-databatcher/ops/shell/db_backup_monthly.sh >> logs/db_backup_monthly.log 2>&1
```
