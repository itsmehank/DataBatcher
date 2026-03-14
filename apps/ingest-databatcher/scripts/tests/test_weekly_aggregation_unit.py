from __future__ import annotations

import datetime as dt

import pandas as pd

from core.date_utils import DateUtils
from scripts.weekly_update import should_skip_latest_week_kst
from core.weekly_aggregation import aggregate_daily_to_weekly_trading_days


class _FixedDateUtils(DateUtils):
    def __init__(self, fixed_now: dt.datetime):
        super().__init__("Asia/Seoul")
        self._fixed_now = fixed_now

    def now(self) -> dt.datetime:
        return self._fixed_now


def _make_daily(symbol: str, dates, opens):
    return pd.DataFrame(
        {
            "date": pd.to_datetime(list(dates)),
            "open": list(opens),
            "high": [o + 10 for o in opens],
            "low": [o - 10 for o in opens],
            "close": [o + 1 for o in opens],
            "volume": [100] * len(opens),
            "market": ["KOSPI"] * len(opens),
            "source": ["pykrx"] * len(opens),
        }
    )


def test_week_start_is_first_trading_day():
    # Monday holiday scenario: only Tue-Fri
    df = _make_daily(
        "AAA",
        ["2024-06-04", "2024-06-05", "2024-06-07"],
        [100, 110, 130],
    )
    weekly = aggregate_daily_to_weekly_trading_days(df, skip_latest_week=False)
    assert len(weekly) == 1
    assert str(weekly.loc[0, "week_start"]) == "2024-06-04"


def test_week_end_is_last_trading_day():
    # Friday holiday scenario: Mon-Thu only
    df = _make_daily(
        "AAA",
        ["2024-06-03", "2024-06-04", "2024-06-06"],
        [100, 110, 120],
    )
    weekly = aggregate_daily_to_weekly_trading_days(df, skip_latest_week=False)
    assert len(weekly) == 1
    assert str(weekly.loc[0, "week_end"]) == "2024-06-06"


def test_skip_latest_week_after_aggregation():
    # Two week groups; max(date) belongs to the second one -> it gets dropped
    df = _make_daily(
        "AAA",
        ["2024-06-03", "2024-06-04", "2024-06-10"],
        [100, 110, 200],
    )
    weekly = aggregate_daily_to_weekly_trading_days(df, skip_latest_week=True)
    # second week dropped -> only first week remains
    assert len(weekly) == 1
    assert str(weekly.loc[0, "week_start"]) == "2024-06-03"


def test_should_skip_latest_week_kst_weekday_true():
    # 2026-01-30 is Friday
    du = _FixedDateUtils(dt.datetime(2026, 1, 30, 12, 0, 0, tzinfo=dt.timezone(dt.timedelta(hours=9))))
    assert should_skip_latest_week_kst(du) is True


def test_should_skip_latest_week_kst_weekend_false():
    # 2026-01-31 is Saturday
    du = _FixedDateUtils(dt.datetime(2026, 1, 31, 12, 0, 0, tzinfo=dt.timezone(dt.timedelta(hours=9))))
    assert should_skip_latest_week_kst(du) is False
