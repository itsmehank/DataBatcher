from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone

import FinanceDataReader as fdr
import pandas as pd
import pandas_market_calendars as mcal


@dataclass
class SymbolCheck:
    symbol: str
    latest_date: str | None
    rows: int
    status: str
    error: str | None = None


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Check when FDR exposes the latest US market date")
    p.add_argument("--stock-symbol", default="AAPL")
    p.add_argument("--index-symbol", default="US500")
    p.add_argument("--lookback-days", type=int, default=10)
    return p.parse_args(argv)


def get_now_et() -> datetime:
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo("America/New_York"))
    except Exception:
        import pytz

        return datetime.now(pytz.timezone("America/New_York"))


def get_latest_closed_session(now_et: datetime) -> tuple[pd.Timestamp | None, bool]:
    cal = mcal.get_calendar("XNYS")
    start_date = (now_et.date() - timedelta(days=10)).isoformat()
    end_date = now_et.date().isoformat()
    schedule = cal.schedule(start_date=start_date, end_date=end_date)
    if schedule.empty:
        return None, False

    now_utc = now_et.astimezone(timezone.utc)
    closed = schedule[schedule["market_close"] <= now_utc]
    if closed.empty:
        return None, False

    latest = closed.index.max()
    today_is_closed_session = latest.date() == now_et.date()
    return latest, today_is_closed_session


def fetch_latest(symbol: str, start_date: str, end_date: str) -> SymbolCheck:
    try:
        df = fdr.DataReader(symbol, start=start_date, end=end_date)
        if df is None or df.empty:
            return SymbolCheck(symbol=symbol, latest_date=None, rows=0, status="empty")

        latest_date = pd.to_datetime(df.index.max()).date().isoformat()
        return SymbolCheck(symbol=symbol, latest_date=latest_date, rows=len(df), status="ok")
    except Exception as e:
        return SymbolCheck(symbol=symbol, latest_date=None, rows=0, status="error", error=str(e))


def main(argv=None) -> int:
    args = parse_args(argv)
    now_kst = datetime.now().astimezone().replace(microsecond=0)
    now_et = get_now_et().replace(microsecond=0)

    latest_closed, today_closed = get_latest_closed_session(now_et)

    print(f"[fdr-us-monitor] now_kst={now_kst.isoformat(sep=' ')}")
    print(f"[fdr-us-monitor] now_et={now_et.isoformat(sep=' ')}")

    if latest_closed is None:
        print("[fdr-us-monitor] status=NO_CLOSED_SESSION")
        return 0

    expected_latest = latest_closed.date().isoformat()
    print(f"[fdr-us-monitor] expected_latest_closed_session={expected_latest}")
    print(f"[fdr-us-monitor] today_closed={today_closed}")

    if not today_closed:
        print("[fdr-us-monitor] status=PRE_CLOSE_OR_NON_TRADING_DAY")
        return 0

    start_date = (latest_closed.date() - timedelta(days=args.lookback_days)).isoformat()
    end_date = expected_latest
    checks = [
        fetch_latest(args.stock_symbol, start_date, end_date),
        fetch_latest(args.index_symbol, start_date, end_date),
    ]

    for check in checks:
        print("[fdr-us-monitor] sample=" + json.dumps(asdict(check), ensure_ascii=False))

    if any(check.status == "error" for check in checks):
        print("[fdr-us-monitor] status=FETCH_ERROR")
        return 1

    if any(check.latest_date is None for check in checks):
        print("[fdr-us-monitor] status=NO_DATA_YET")
        return 0

    latest_dates = {check.latest_date for check in checks}
    if len(latest_dates) != 1:
        print("[fdr-us-monitor] status=INCONSISTENT_SAMPLES")
        return 1

    observed_latest = latest_dates.pop()
    print(f"[fdr-us-monitor] observed_latest={observed_latest}")

    if observed_latest == expected_latest:
        print("[fdr-us-monitor] status=AVAILABLE")
        return 0

    print("[fdr-us-monitor] status=NOT_YET_AVAILABLE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
