# AGENTS.md

## Scope
- This file provides instructions for coding agents working in this repository root.
- Apply these rules to both `frontend/` and `backend/` unless a section says otherwise.

## Rule Files Discovery
- Checked `.cursor/rules/`: not present.
- Checked `.cursorrules`: not present.
- Checked `.github/copilot-instructions.md`: not present.
- No external Cursor/Copilot rule files exist, so this file is the canonical agent guide.

## Repository Structure
- `frontend/`: Next.js 15 App Router + React 19 + TypeScript.
- `backend/`: NestJS 10 + Mongoose + TypeScript.
- `docs/`: API, security, backup, and refactor documentation.
- `docker-compose.yml`: local multi-service orchestration.

## Toolchain Facts
- Package manager: npm (lockfiles present in `frontend/` and `backend/`).
- TypeScript strict mode is enabled in both apps.
- Frontend uses standalone output (`frontend/next.config.ts`).
- No first-party test files are currently present in app source.

## Setup Commands
- Install frontend dependencies:
  - `npm --prefix frontend install`
- Install backend dependencies:
  - `npm --prefix backend install`

## Build Commands
- Frontend build:
  - `npm --prefix frontend run build`
- Backend build:
  - `npm --prefix backend run build`
- Recommended before shipping changes: run both builds.

## Lint Commands
- There is currently no lint script configured in either `package.json`.
- If you add linting, prefer scripts named:
  - `lint`
  - `lint:fix`
- If added, update this file and `README.md` in the same change.

## Test Commands
- There is currently no test runner script configured.
- There are no project tests under `frontend/` or `backend/src/` right now.
- Do not invent test results; state clearly when tests are unavailable.

## Single Test Guidance (Current + Future)
- Current state: single-test execution is not available because test infra is absent.
- If you introduce tests, also introduce scripts to support single test runs.
- Recommended future script patterns:
  - `npm --prefix backend run test -- entries.service.spec.ts`
  - `npm --prefix frontend run test -- app/page.test.tsx`
- Keep single-test instructions updated here once real test tooling exists.

## Dev Run Commands
- Frontend dev server:
  - `npm --prefix frontend run dev`
- Backend dev server:
  - `npm --prefix backend run start:dev`
- Backend runtime requires valid environment values for:
  - `JWT_SECRET`
  - `MONGODB_URI`

## Production Run Commands
- Frontend (standalone build):
  - `npm --prefix frontend run build`
  - `PORT=3000 npm --prefix frontend run start`
- Note: avoid `next start` directly for this repo because frontend uses standalone output.
- Backend production:
  - `npm --prefix backend run build`
  - `npm --prefix backend run start`

## Environment and Secrets
- Copy `.env.example` to `.env` for local setup.
- Never commit `.env` or secrets.
- `.gitignore` already excludes `.env`, `.env.*`, `node_modules`, `.next`, `dist`, `backups`.
- `JWT_SECRET` is mandatory in backend auth modules; startup fails when missing.
- Docker `.env` example uses `mongodb` hostname; local non-docker runs may need localhost URI.

## Verification Commands
- Backend health check:
  - `curl -i http://localhost:4000/api/health`
- Frontend route smoke checks (manual or curl):
  - `/`
  - `/templates`
  - `/login`
  - `/admin`
- Optional 404 sanity check:
  - `/entries/non-existent-id`

## Code Style: General
- Use TypeScript everywhere; preserve strict typing.
- Prefer small, focused modules and predictable control flow.
- Avoid `any`; use explicit interfaces/types or `unknown` with narrowing.
- Keep behavior-preserving refactors isolated from feature changes.
- Use ASCII by default unless file already requires non-ASCII.

## Imports
- Prefer import grouping order:
  1) framework/external packages
  2) internal modules
  3) type-only imports when helpful (`import type`)
- Remove unused imports immediately.
- Keep relative path style consistent with nearby files.

## Formatting
- Follow existing formatting in touched files.
- Use semicolons and trailing commas where already used.
- Keep lines readable; avoid dense one-liners for complex logic.
- Do not introduce unrelated formatting churn.

## Naming Conventions
- React components: PascalCase (`ArchiveToolbar`).
- Hooks: `useXxx` (`useArchiveData`).
- Variables/functions: camelCase.
- Class names (Nest DTO/schema/module/service/controller): PascalCase.
- Constants: UPPER_SNAKE_CASE only for true constants.
- Filenames: use existing project conventions (kebab-case in feature files; framework names like `page.tsx`).

## Frontend Conventions
- Keep page files orchestration-focused.
- Put reusable page logic into `frontend/features/*/hooks`.
- Put reusable UI pieces into `frontend/features/*/components`.
- Shared types in `frontend/types/`.
- Shared utilities in `frontend/lib/`.
- Use `api<T>()` helper for HTTP calls; keep response typing explicit.

## Backend Conventions
- Keep Nest layering clear: controller -> service -> model.
- Put request payload shapes in DTO classes.
- Throw typed Nest exceptions for error cases.
- Keep ownership/authorization checks in service-level mutation paths.
- Keep API contract consistent with `docs/API.md`.

## Error Handling
- Frontend:
  - Use `try/catch` for async API calls.
  - Show actionable user-facing messages.
  - Treat auth failures explicitly (login hint/redirect flows).
- Backend:
  - Use `BadRequestException`, `UnauthorizedException`, `ForbiddenException`, `NotFoundException` as appropriate.
  - Avoid silent fallbacks for security-critical configuration.

## API and Data Rules
- Backend routes are served under `/api` prefix.
- Keep enum-like values stable (`chatgpt`, `claude`, `gemini`, `other`).
- When changing request/response shapes, update docs in the same change.

## CSS and UI Rules
- Keep global tokens/layout in `frontend/app/globals.css`.
- Keep page-specific styles in `frontend/app/styles/*.css`.
- Scope page-specific selectors with root page classes to avoid collisions.
- Validate both desktop and mobile layout behavior when changing styles.

## Change Safety for Agents
- Do not revert unrelated local changes.
- Do not perform destructive git operations unless explicitly requested.
- Keep commits/task diffs focused and reviewable.
- Call out limitations clearly (missing tests, env prerequisites, external services).

## Definition of Done (Agent Checklist)
- Relevant code updated with minimal scope.
- Frontend and backend build commands pass.
- Runtime sanity checks pass for touched flows.
- No secrets added to tracked files.
- Docs updated if commands/contracts/workflows changed.
