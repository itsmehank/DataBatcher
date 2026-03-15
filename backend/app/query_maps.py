from __future__ import annotations

REGION_TABLES = {
    "US": {
        "symbol_master": "us_symbol_master",
        "minervini": "minervini_screen_results_us",
        "daily_view": "v_us_stock_price_with_ma",
        "weekly_view": "v_us_stock_price_weekly_with_ma",
        "price_daily": "us_stock_prices",
        "index_daily": "us_index_prices",
    },
    "KR": {
        "symbol_master": "symbol_master",
        "minervini": "minervini_screen_results_kr",
        "daily_view": "v_stock_price_with_ma",
        "weekly_view": "v_stock_price_weekly_with_ma",
        "price_daily": "stock_prices",
        "index_daily": "kr_index_prices",
    },
}


def get_region_tables(region: str) -> dict[str, str]:
    key = region.upper()
    if key not in REGION_TABLES:
        raise ValueError("Invalid region")
    return REGION_TABLES[key]
