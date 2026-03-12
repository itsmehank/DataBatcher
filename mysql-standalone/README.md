# MySQL Standalone (Docker Compose)

This directory is a standalone MySQL project extracted from the original Grafana + MySQL setup.

## Files

- `docker-compose-mysql.yaml`: MySQL-only Docker Compose file
- `../.env.example`: Root environment template (single source of truth)
- `mysql/my.cnf`: MySQL server configuration
- `mysql/init/setup.sh`: Extra bootstrap for `${MYSQL_DATABASE}_test` grants
- `../docker/mysql/init/01_schema.sql`: DataBatcher main schema (mounted into init dir)

## Quick Start

1. Prepare root env file (single source of truth).
   Run this command from project root:

   ```bash
   cp .env.example .env
   ```

2. Update values in root `.env` (at minimum `MYSQL_ROOT_PASSWORD`, `MYSQL_PASSWORD`, `DATABASE_URL`).

   Keep these values aligned:
   - `MYSQL_DATABASE` == database name in `DATABASE_URL`
   - `MYSQL_PORT` == port in `DATABASE_URL`

3. Start MySQL from project root:

   ```bash
   docker compose -f mysql-standalone/docker-compose-mysql.yaml --env-file .env up -d
   ```

   If port `3306` is already in use, you can run temporary port override:

   ```bash
   MYSQL_PORT=3307 docker compose -f mysql-standalone/docker-compose-mysql.yaml --env-file .env up -d
   ```

   In that case, update `DATABASE_URL` port to `3307` too if app scripts should target this MySQL.

4. Check status:

   ```bash
   docker compose -f mysql-standalone/docker-compose-mysql.yaml --env-file .env ps
   ```

5. View logs:

   ```bash
   docker compose -f mysql-standalone/docker-compose-mysql.yaml --env-file .env logs -f mysql
   ```

6. Stop service:

   ```bash
   docker compose -f mysql-standalone/docker-compose-mysql.yaml --env-file .env down
   ```

## Notes

- Data is persisted in the named volume `mysql_data`.
- This compose and DataBatcher scripts share the same root `.env` values.
- Init scripts run only on first initialization (when volume is empty):
  - `01_schema.sql` creates DataBatcher tables/views.
  - `setup.sh` creates `${MYSQL_DATABASE}_test` and grants test DB privileges.
- Auth still uses `MYSQL_*` credentials from root `.env` (password-based login).
- If schema changes after first init, re-apply with `python scripts/init_db.py` (or reset volume).
- To fully reset data, run:

  ```bash
  docker compose -f mysql-standalone/docker-compose-mysql.yaml --env-file .env down -v
  ```
