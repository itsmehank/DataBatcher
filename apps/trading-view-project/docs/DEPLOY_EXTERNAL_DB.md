# Deploy With External DB

This deployment mode runs only the app services (backend + frontend).
Database provisioning, schema/view setup, and data initialization are managed externally.

## Prerequisites

- External MySQL is reachable from the backend runtime
- Required DB objects already exist (see `backend/app/query_maps.py`)
- Docker and Docker Compose are installed

## Required environment

Create `backend/.env` from `backend/.env.example` and set:

- `DATABASE_URL`
- `ALLOWED_ORIGINS`
- `SECRET_KEY` (required if auth is enabled)
- `ADMIN_USERNAME` and `ADMIN_PASSWORD` (optional startup bootstrap; set both or neither)

Example:

```env
DATABASE_URL=mysql+pymysql://<db_user>:<db_password>@<db_host>:3306/<db_name>?charset=utf8mb4
ALLOWED_ORIGINS=http://localhost:5173
SECRET_KEY=CHANGE_ME_RANDOM_SECRET_AT_LEAST_32_CHARS
ADMIN_USERNAME=admin
ADMIN_PASSWORD=CHANGE_ME_STRONG_PASSWORD
```

## Optional auth bootstrap prerequisites

- `db/init/02_auth_schema.sql` must already be applied if you want login/admin bootstrap.
- The backend DB user must have `SELECT`, `INSERT`, and `UPDATE` permissions on `users`.
- Startup bootstrap is best-effort. If bootstrap fails, the server still starts and public read endpoints remain available.
- `scripts/create_user.py` remains the manual recovery path.

## Start services

From project root:

```bash
docker compose --env-file backend/.env up -d --build
```

Services:

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`

## Validate external DB readiness

- App liveness: `GET /api/health`
- DB readiness: `GET /api/health/db?region=US`
- Optional KR check: `GET /api/health/db?region=KR`

If required objects are missing, `/api/health/db` returns `503` with object names.

## Stop services

```bash
docker compose down
```
