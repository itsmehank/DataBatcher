# Run Backend + Frontend Together

This project includes `run-dev.sh` so you can start both services with one command.

## Prerequisites

- External MySQL is running and reachable
- Backend virtualenv exists (`backend/.venv`)
- Frontend dependencies installed (`frontend/node_modules`)

## First-time setup

### 1) Backend setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Frontend setup

```bash
cd frontend
npm install
```

## Run both services

From the project root (`minervini-lwc-dashboard`):

```bash
chmod +x run-dev.sh
./run-dev.sh
```

Default addresses:

- Backend API: `http://localhost:8000`
- Frontend UI: `http://localhost:5173`

## Stop services

Press `Ctrl + C` in the same terminal.
The script traps the signal and stops the backend process.

## Optional custom ports

```bash
BACKEND_PORT=8002 FRONTEND_PORT=5174 ./run-dev.sh
```

## Troubleshooting

- `backend/.venv not found`
  - Run the backend setup section.
- `frontend/node_modules not found`
  - Run `cd frontend && npm install`.
- `Address already in use`
  - Change ports with `BACKEND_PORT` and `FRONTEND_PORT`.
- DB connection error
  - Check `DATABASE_URL` in `backend/.env` first.
  - Repo root `.env` is for shared MySQL bootstrap and should not be treated as the primary runtime config for this app.
