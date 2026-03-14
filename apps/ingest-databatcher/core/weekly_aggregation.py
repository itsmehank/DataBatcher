from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd


@dataclass(frozen=True)
class WeeklyAggregationResult:
    """Internal helper shape for debugging/tests."""

    weekly_df: pd.DataFrame
    latest_week_key: Optional[pd.Period]


def aggregate_daily_to_weekly_trading_days(
    daily_df: pd.DataFrame,
    *,
    skip_latest_week: bool = True,
) -> pd.DataFrame:
    """Aggregate daily OHLCV rows into weekly OHLCV rows.

    Source-of-truth contract used by weekly scripts:
    - week_start is NOT fixed Monday; it is the first trading day in that week.
    - week_end is the last trading day in that week.

    Rules (as per docs/weekly_aggregation_refactor_plan.md):
    - week_key: date.to_period('W-FRI') (keep Period type; do not stringify)
    - week_start: first trading day of the week (min(date) within week_key)
    - week_end: last trading day of the week (max(date) within week_key)
    - open: open of first trading day
    - close: close of last trading day
    - high/low: max/min within the week
    - volume: sum within the week
    - adj_close (if present): last within the week
    - market/source (if present): first within the week

    Latest week skipping (A안):
    - Determine latest_week_key from daily_df['date'].max().to_period('W-FRI')
    - Aggregate first, then drop rows with that week_key

    Args:
        daily_df: DataFrame containing at least: date, open, high, low, close, volume
        skip_latest_week: Drop the latest week_key (derived from max(date)) after aggregation

    Returns:
        Weekly aggregated DataFrame.
        Columns: week_start, week_end, open, high, low, close, volume, [adj_close], [market], [source]

    Notes:
        - Returns empty DataFrame when input is empty or when everything is dropped.
    """

    if daily_df is None or daily_df.empty:
        return pd.DataFrame()

    df = daily_df.copy()
    if "date" not in df.columns:
        raise ValueError("daily_df must contain 'date' column")

    # Normalize datetime and sort (needed for first/last)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    # week_key: keep Period type
    df["week_key"] = df["date"].dt.to_period("W-FRI")

    latest_week_key: Optional[pd.Period] = None
    if skip_latest_week:
        latest_day = df["date"].max()
        if pd.notna(latest_day):
            latest_week_key = pd.Timestamp(latest_day).to_period("W-FRI")

    # Aggregation
    agg_dict = {
        "date": ["min", "max"],
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": lambda s: s.sum(min_count=1),
    }
    if "adj_close" in df.columns:
        agg_dict["adj_close"] = "last"
    if "market" in df.columns:
        agg_dict["market"] = "first"
    if "source" in df.columns:
        agg_dict["source"] = "first"

    weekly = df.groupby("week_key").agg(agg_dict).reset_index()

    # Flatten multiindex columns
    cols = []
    for c in weekly.columns:
        if isinstance(c, tuple):
            # e.g. ('date', 'min')
            if c[0] == "date" and c[1] == "min":
                cols.append("week_start")
            elif c[0] == "date" and c[1] == "max":
                cols.append("week_end")
            else:
                cols.append(c[0])
        else:
            cols.append(c)
    weekly.columns = cols

    # Ensure week_start/week_end are date (not timestamp)
    weekly["week_start"] = pd.to_datetime(weekly["week_start"]).dt.date
    weekly["week_end"] = pd.to_datetime(weekly["week_end"]).dt.date

    # Drop latest week AFTER aggregation (as per plan)
    if skip_latest_week and latest_week_key is not None:
        weekly = weekly[weekly["week_key"] != latest_week_key]

    # Drop internal column
    if "week_key" in weekly.columns:
        weekly = weekly.drop(columns=["week_key"])

    return weekly
