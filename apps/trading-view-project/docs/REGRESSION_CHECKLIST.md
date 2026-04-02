# Regression Checklist

Use this checklist after refactors that touch API, dashboard state flow, or chart rendering.

## Automated checks

- Backend: `cd backend && ./.venv/bin/pytest`
- Frontend: `cd frontend && npm run test && npm run typecheck && npm run build`

## Manual smoke checks

- Open `http://localhost:5173/dashboard`
- Open `http://localhost:5173/list-view`
- Verify backend health: `GET /api/health` returns `200`
- Verify options endpoint: `GET /api/options/markets?region=US` returns `200`

## Dashboard flow

- Region/date/market/listCategory/symbol changes update URL query params correctly
- Changing symbol quickly does not flash stale chart data
- Daily/weekly "load more history" works and does not loop duplicate requests
- List type toggle in filtered view updates rows immediately and rolls back on API failure
- ZIP export succeeds and excludes `.no-export` area
- File export attempts image + 3 CSV downloads for the active symbol

## List View flow

- Region/date/listCategory changes update URL query params correctly
- Selecting a symbol updates the lower chart area without navigating away
- Row save works for trigger/stop/status/memo fields
- Invalid update payloads surface API error messages

## Chart View flow

- Region/market/category/symbol changes update URL query params correctly
- Symbol name box follows the selected ticker
- Daily/RS/Weekly charts load for the selected ticker

## API contract spot checks

- `/api/minervini` still returns `ticker,name,market,sector,rs_rating,is_blue_dot,category_val,list_type`
- `/api/chart/daily` keeps `candles,volume,indicators,meta` response structure
- Error payload shape remains `{ "detail": "..." }`
