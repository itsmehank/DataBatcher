# AGENTS.md

This file is for coding agents working in `minervini-lwc-dashboard`.
Follow these conventions to keep changes safe, testable, and consistent.

## 1) Project overview

- Monorepo-style layout with separate backend and frontend apps.
- Backend: FastAPI + SQLAlchemy Core + PyMySQL.
- Frontend: React + TypeScript + Vite + lightweight-charts.
- Runtime DB is external MySQL, configured via env vars.

## 2) Repository layout

- `backend/app/` - FastAPI app code.
- `backend/tests/` - pytest API contract and behavior tests.
- `frontend/src/` - React app code.
- `frontend/src/**/*.test.ts` - Vitest unit tests.
- `docs/` - API contract, regression checklist, deploy docs.
- `run-dev.sh` - local dev runner for backend + frontend.

## 3) Cursor/Copilot rules

- No `.cursor/rules/`, `.cursorrules`, or `.github/copilot-instructions.md` files are present.
- If such files are added later, treat them as higher-priority repo rules and update this document.

## 4) Environment and setup

- Backend required env vars:
  - `DATABASE_URL`
  - `ALLOWED_ORIGINS` (comma-separated)
- Use `backend/.env.example` as template.
- For Docker deploy with external DB, see `docs/DEPLOY_EXTERNAL_DB.md`.

## 5) Build, test, and run commands

### Backend (from `backend/`)

- Install deps:
  - `pip install -r requirements.txt`
  - `pip install -r requirements-dev.txt`
- Run dev server:
  - `uvicorn app.main:app --reload --port 8000`
- Run full test suite:
  - `./.venv/bin/pytest`
  - or `pytest` (if venv activated)

### Backend single-test commands

- Run one test file:
  - `./.venv/bin/pytest tests/test_chart_and_errors.py`
- Run one test function:
  - `./.venv/bin/pytest tests/test_chart_and_errors.py::test_health_db_success`
- Run tests matching expression:
  - `./.venv/bin/pytest -k "health_db and not missing"`

### Frontend (from `frontend/`)

- Install deps:
  - `npm install`
- Run dev server:
  - `npm run dev`
- Run all unit tests:
  - `npm run test`
- Type-check:
  - `npm run typecheck`
- Production build:
  - `npm run build`

### Frontend single-test commands

- Run one test file:
  - `npm run test -- src/api.test.ts`
- Run one named test:
  - `npm run test -- -t "uses JSON detail message when present" src/api.test.ts`

### Full verification before merge

- Backend:
  - `cd backend && ./.venv/bin/pytest`
- Frontend:
  - `cd frontend && npm run test && npm run typecheck && npm run build`

## 6) API and contract constraints

- Keep API paths stable under `/api/*`.
- Keep query parameter names stable (`date`, `listCategory`, `from`, `to`, etc.).
- Keep response key names stable for list/chart payloads.
- Keep error response shape stable: `{ "detail": ... }`.
- Reference: `docs/API.md`.

## 7) Code style guidelines

### General

- Prefer small, focused changes with clear intent.
- Do not mix refactor + behavior change in one patch unless required.
- Keep compatibility with existing endpoint and UI behavior.

### Imports

- Use absolute-relative style already used in repo (`../...`, `./...`).
- Group imports by category:
  1. external packages
  2. internal modules
  3. type imports (`import type ...`)
- Remove unused imports immediately.

### Formatting and structure

- Follow existing formatter output (2 spaces for TS/TSX, Black-like style for Python).
- Prefer early returns to reduce nesting.
- Keep functions short; extract reusable logic into `lib/`, `hooks/`, or router helpers.
- Avoid comments unless logic is non-obvious.

### TypeScript and React

- Avoid `any`; use concrete types and narrow with guards.
- Keep props and state typed explicitly.
- Prefer `useMemo` for expensive/identity-sensitive derived arrays/objects.
- Prefer `useCallback` for handler stability when passed to children.
- Keep page components thin; move orchestration into hooks.
- For query-param bootstrap, use helper utilities (`src/lib/queryState.ts`).

### Python and FastAPI

- Add type hints for public functions and route handlers.
- Keep route modules focused by domain (`routers/options.py`, `routers/minervini.py`, `routers/chart.py`).
- Reuse common parsing/validation helpers from `app/common.py`.
- Use parameterized SQL; never inject user values directly.

### Naming

- TS/TSX:
  - Components: `PascalCase`
  - Hooks: `useXxx`
  - Variables/functions: `camelCase`
  - Constants: `UPPER_SNAKE_CASE` only for true constants.
- Python:
  - Modules/functions/variables: `snake_case`
  - Classes: `PascalCase`

### Error handling

- Backend:
  - Raise `HTTPException` for input/domain errors.
  - Let global handlers map `ValueError` and `SQLAlchemyError` consistently.
- Frontend:
  - Surface readable error messages from API (`detail` first, fallback text/status).
  - Preserve abort handling patterns for in-flight request cancellation.

## 8) Testing expectations for changes

- Any API behavior change must include/adjust pytest coverage.
- Any utility/hook logic change should include/adjust Vitest coverage.
- For risky UI async changes, run manual checklist in `docs/REGRESSION_CHECKLIST.md`.

## 9) Deployment expectations

- External DB only; do not add local DB assumptions to compose/deploy docs.
- Keep `docker-compose.yml` focused on app services (backend/frontend).
- Validate DB readiness through `/api/health/db?region=US` (and KR when needed).

## 10) Authentication

### Overview

- Cookie-based JWT authentication via HttpOnly Secure SameSite=Lax cookies.
- Roles: `viewer` (read-only), `editor` (read + write APIs).
- Auth module: `backend/app/auth/` (password, token, cookie, dependencies).
- Auth router: `backend/app/routers/auth.py` — `/api/auth/login`, `/api/auth/logout`, `/api/auth/me`.

### Environment variables

- `SECRET_KEY` (required for auth): JWT signing key, minimum 32 characters.
- `ACCESS_TOKEN_EXPIRE_MINUTES` (default: 1440 = 24h): Token lifetime.
- `COOKIE_SECURE` (default: false): Set to `true` in production (HTTPS).

### Protecting endpoints

- Use `Depends(require_editor)` on write endpoints (POST/PATCH/PUT/DELETE).
- GET endpoints remain public (no auth required).
- Error responses: `401 {"detail": "Not authenticated"}`, `403 {"detail": "Insufficient permissions"}`.

### User management

- Create users via CLI: `python -m scripts.create_user --username <name> --password <pw> --role editor`
- No registration UI — admin creates accounts manually.
- Account lockout: 5 consecutive failures → 15 minute lock.

### Rate limiting

- Login endpoint (`POST /api/auth/login`): 5 requests per minute per IP.
- Implemented via `Depends(check_login_rate_limit)` in `app/rate_limit.py`.
- Returns `429 {"detail": "Too many login attempts. Try again later."}` when exceeded.
- Memory-based (resets on server restart). For multi-server, switch to Redis.

### CORS (production)

- Set `ALLOWED_ORIGINS` to your production domain(s) before deploying.
- Example: `ALLOWED_ORIGINS=https://trading.yourdomain.com`
- Startup warning is logged if `COOKIE_SECURE=true` with localhost origins.
- Never use `*` — `allow_credentials=True` requires explicit origins.

### Frontend

- `AuthContext` (React Context) manages auth state via `/api/auth/me` on mount.
- Write UI (select, input, save buttons) is disabled for non-editor users.
- All fetch calls use `credentials: "include"` for cookie transmission.
- Login page: `/login` route.
