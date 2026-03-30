# AGENTS.md

## Purpose
This file guides coding agents working in this repository.
Follow these conventions unless the user explicitly asks otherwise.

## Language Policy
- Default response language is Korean.
- Use another language only when the user explicitly requests it.

## Repository Snapshot
- Main language: Python (3.9)
- Main domain: Korean real-estate transaction ingestion, analysis, and surge detection
- Core runtime dependencies: `mysql-connector-python`, `pandas`, `numpy`, `python-dateutil`, `requests`, `flask`, `folium`
- Database: shared MySQL instance with dedicated `real_estate` / `real_estate_test` databases
- UI: Flask app in `web_ui/`
- Schema SSOT: `db/init/03_real_estate_schema.sql`
- Deployment automation: out of scope in this monorepo task set
- Data collection scripts: `scripts/collect_initial.sh`, `scripts/collect_daily.sh`
- Nginx example config: `ops/nginx/real-estate.conf`
- Public release checklist: `docs/public_release_checklist.md`

## Rule Files Check
- `.cursor/rules/`: not found
- `.cursorrules`: not found
- `.github/copilot-instructions.md`: not found
- `CLAUDE.md`: present and should be treated as project guidance

## Working Directories
- App root in this monorepo: `apps/real-estate-project/`
- When starting from the monorepo root, `cd apps/real-estate-project` first unless a command already includes the full path.
- Root scripts: run from the app root
- Web UI: run from `web_ui/`
- Building query tests: run from `building_query/` or root with module imports

## Environment Setup
- Create venv:
  - `python3 -m venv .venv`
  - `source .venv/bin/activate`
- Install runtime dependencies:
  - `pip install -r requirements.txt`
- Optional extra install for web-only workflows:
  - `pip install -r web_ui/requirements.txt`
- Python version target in this repo appears to be 3.9.x.

## Build Commands
There is no formal packaging/build system (`pyproject.toml`, `setup.py`, `Makefile` not present).

Use these "build-like" sanity checks:
- Syntax check a file:
  - `python -m py_compile src/real_estate/cli.py`
- Syntax check whole repo (may create `__pycache__`):
  - `python -m compileall .`

## Lint / Format Commands
No linter/formatter config is checked in (no `ruff`, `flake8`, `black`, `isort`, `mypy` config).

If user asks for linting, use safe ad-hoc checks:
- Basic style/syntax smoke:
  - `python -m py_compile web_ui/app.py`
- Optional local lint if installed manually:
  - `ruff check .`
  - `black --check .`

Do not assume lint tools exist unless installed in the current environment.

## Test Commands
This repo has a formal pytest suite under `tests/` and also keeps a few ad-hoc utility scripts.

### Preferred pytest suite
- Run unit + non-DB integration tests:
  - `pytest -q tests -m "not db"`
- Run DB integration tests:
  - `pytest -q tests -m db`

### Supplemental utility scripts
- Building query smoke script:
  - `python building_query/test_building_query.py`
- Web UI dummy-mode server smoke script:
  - `python web_ui/test_app.py`
  - Then verify `GET http://localhost:5002/health`

## Main Runtime Commands
- The commands below assume the current working directory is `apps/real-estate-project/`.
- For direct CLI commands, load runtime env first:
  - `set -a && source .env && set +a`
- Run main Flask app:
  - `python -m src.real_estate.cli serve-web --port 5001`
- Production deployment expectation:
  - Run Flask on `127.0.0.1:5001` behind Nginx (`ops/nginx/real-estate.conf`)
- Re-apply DB schema when recovery/manual DDL sync is needed:
  - `python -m src.real_estate.cli init-db`
- Run schema SQL directly (DBA/manual):
  - `mysql -u <user> -p <target_db> < ../../db/init/03_real_estate_schema.sql`
- Run ingestion pipeline:
  - `python -m src.real_estate.cli ingest --lawd-cds 11650 --start-ymd 202401 --end-ymd 202402`
- Run analyzer pipeline:
  - `python -m src.real_estate.cli analyze`
- Run anomaly correction:
  - `python -m src.real_estate.cli clean-anomalies`
- Run recalculation:
  - `python -m src.real_estate.cli recalculate-derived`

## Code Style Guidelines

### Imports
- Preferred order:
  1) Python stdlib
  2) Third-party libs
  3) Local project imports
- One import per line for readability.
- Avoid unused imports.
- Keep `sys.path.append(...)` usage minimal and only where already required by project structure.

### Formatting
- Follow existing style: PEP 8-ish, 4-space indentation.
- Keep lines readable; avoid dense one-liners.
- Preserve Korean comments/docstrings where surrounding code uses Korean.
- Do not introduce unrelated reformat churn in touched files.

### Types
- Type hints are partial in this repo; keep consistency with file context.
- Add type hints for new/modified public methods when practical.
- Avoid large, invasive typing refactors unless requested.
- Prefer explicit return types for utility functions.

### Naming
- Classes: `PascalCase` (e.g., `CombinedSurgeDetector`)
- Functions/variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- DB config names currently follow existing pattern:
  - `DB_CONNECTION_INFO`, `DB_CONFIG`
- Keep domain field names aligned with DB schema (`sggCd`, `umdNm`, `deal_ymd`, etc.) when mapping DataFrames/SQL rows.

### SQL and Database
- Shared bootstrap DDL lives in `db/init/03_real_estate_schema.sql`.
- Do not add or modify inline `CREATE TABLE` SQL across multiple modules.
- If schema changes are needed, update `db/init/03_real_estate_schema.sql` first.
- Prefer parameterized queries (`%s` placeholders) for user/input-derived values.
- Reuse existing transaction patterns:
  - explicit commit on success
  - rollback on exceptions
- Always close cursor/connection in `finally` or context managers.
- Keep schema/table naming consistent with existing tables.

### Pandas/Data Processing
- Validate emptiness with `df.empty` before downstream operations.
- Preserve sorting before time-series calculations (`deal_ymd` ordering matters).
- Replace/handle `NaN` and inf before DB writes where needed.
- Keep column names stable; many downstream scripts rely on exact names.

### Error Handling
- Catch specific exceptions when possible (`mysql.connector.Error`, `ValueError`, request exceptions).
- Avoid broad bare `except:` in new code.
- Return safe empty structures (`pd.DataFrame()`, `{}`) where existing patterns expect them.
- Include contextual information in error logs (region/date/building keys).

### Logging / Output
- Existing code uses `print`; follow local pattern unless user requests logging framework migration.
- Keep operational logs concise and action-oriented.
- Do not print secrets or raw credentials.

### Flask/Web UI
- Keep API response structure stable (`success`, `message`, `data`).
- Validate request JSON parameters and date formats (`%Y%m`).
- Handle empty analysis results gracefully with success response and empty data.
- `RE_FLASK_SECRET` is required for real web execution; do not reintroduce weak fallbacks.

### Security and Secrets
- Do not add new hardcoded secrets.
- Existing files contain hardcoded API/DB values; treat them as sensitive and avoid spreading them.
- Never commit `.env`, credentials, or tokens unless user explicitly requests and understands risk.
- Prefer environment variables for new credentials.

### File/Change Hygiene
- Keep edits minimal and scoped to requested task.
- Preserve backward compatibility for script entrypoints (`if __name__ == "__main__"`).
- Do not rename core files casually; many scripts are invoked directly by filename.

## Agent Checklist Before Finishing
- Ran the most relevant script/test for changed area.
- For single-test validation, executed direct function invocation where possible.
- Verified no accidental secret exposure in diffs.
- Kept DB schema/column compatibility intact.
- Documented any commands not run and why.
