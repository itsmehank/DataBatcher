# API Contract (MVP)

Base URL: `http://localhost:8000`

## Contract invariants

The following are compatibility-sensitive and should not change without a coordinated frontend update:

- Endpoint paths under `/api/*`
- Query parameter names (`date`, `listCategory`, `from`, `to`, etc.)
- Response key names for list/chart payloads
- Error response shape: `{ "detail": "..." }`

## Health

- `GET /api/health`
- `GET /api/health/db?region=US`

Error behavior:

- Input validation errors: HTTP `400` with `{ "detail": "..." }`
- Not found conditions (where applicable): HTTP `404` with `{ "detail": "..." }`
- Database-level unhandled errors: HTTP `500` with `{ "detail": "Database error" }`

## Option endpoints

- `GET /api/options/dates?region=US`
- `GET /api/options/markets?region=US`
- `GET /api/options/categories?region=US&market=NYSE`
- `GET /api/symbols?region=US&market=NYSE&category=A`

## Minervini list

- `GET /api/minervini?region=US&date=2026-02-13&market=NYSE`
- `POST /api/minervini/list-type`

POST body:

```json
{
  "region": "US",
  "date": "2026-02-13",
  "market": "NYSE",
  "symbol": "AAPL",
  "list_type": "focus"
}
```

`list_type` can be `focus`, `action`, `pass`, or `null` (`null` deletes selection row).

Response item fields:

- `ticker`
- `name`
- `market`
- `sector`
- `rs_rating`
- `is_blue_dot`
- `category_val`
- `list_type`

## List view endpoints

- `GET /api/list-view/dates?region=US`
- `GET /api/list-view/items?region=US&date=2026-02-13&listCategory=all`
- `PATCH /api/list-view/item`

`GET /api/list-view/items` response fields:

- `symbol`, `name`, `market`, `list_type`, `sector`, `rs_rating`
- `trigger_price`, `stop_price`, `status_tag`, `memo`

`PATCH /api/list-view/item` body fields:

- key fields: `region`, `date`, `market`, `symbol`
- editable fields: `trigger_price`, `stop_price`, `status_tag`, `memo`
- `status_tag` allowed values: `A`, `B`, `C`, `D`, `E`, `null`

## Chart endpoints

- `GET /api/chart/daily?region=US&symbol=AAPL&from=2024-01-01&to=2026-02-20`
- `GET /api/chart/weekly?region=US&symbol=AAPL&from=2021-01-01&to=2026-02-20`

Default ranges when `from`/`to` are omitted:

- Daily: recent 6 months
- Weekly: recent 2 years

Chart response fields:

- `symbol`
- `timeframe`
- `from`
- `to`
- `candles[]`: `{ time, open, high, low, close }`
- `volume[]`: `{ time, value, color }`
- `indicators`: map of indicator name -> `{ time, value }[]`
- `meta` (optional): extra chart metadata
  - `meta.rs_1y_high`: `{ time, value } | null` (latest-date anchored 1-year RS high)

Indicator keys currently used:

- Daily: `sma_50`, `sma_100`, `sma_150`, `sma_200`, `rs_line`, `volume_sma_50`
- Weekly: `sma_10`, `sma_20`, `sma_50`, `sma_100`, `sma_200`, `ema_21`, `volume_sma_10`
