# core/date_utils.py
from __future__ import annotations
import datetime as dt
from datetime import date, datetime, timedelta, timezone
import pytz
import pandas_market_calendars as mcal


class DateUtils:
    """Minimal date/time and market calendar utilities for v5 scope.

    - Supports XKRX and NYSE calendars for business-day checks.
    - Provides market-close-with-buffer guard for daily jobs.
    """

    def __init__(self, tz_name: str = "Asia/Seoul"):
        self.tz = pytz.timezone(tz_name)
        # Calendar codes: XKRX (KR), XNYS (NYSE)
        self._calendars = {
            "XKRX": mcal.get_calendar("XKRX"),
            "NYSE": mcal.get_calendar("XNYS"),
        }

    def now(self) -> dt.datetime:
        return dt.datetime.now(self.tz)

    def is_market_open(self, market_code: str, date: dt.date) -> bool:
        cal = self._calendars[market_code]
        schedule = cal.schedule(start_date=date, end_date=date)
        return not schedule.empty

    def get_last_business_day(self, market_code: str, ref: dt.date | None = None) -> dt.date:
        ref = ref or self.now().date()
        cal = self._calendars[market_code]
        # Look back up to 10 days to find last valid session
        schedule = cal.schedule(start_date=ref - dt.timedelta(days=10), end_date=ref)
        return schedule.index.max().date()

    def get_last_closed_business_day(
        self,
        market_code: str,
        local_close_hhmm: str,
        buffer_minutes: int = 30,
        ref: dt.date | None = None,
    ) -> dt.date:
        """마감 완료 기준으로 마지막 영업일 반환.

        Rules:
        - 장 마감 + 버퍼 이전: 전 영업일
        - 장 마감 + 버퍼 이후: 당일(영업일인 경우) 또는 직전 영업일
        """
        base_ref = ref or self.now().date()
        if self.after_market_close_with_buffer(market_code, local_close_hhmm, buffer_minutes):
            return self.get_last_business_day(market_code, ref=base_ref)
        return self.get_last_business_day(market_code, ref=base_ref - dt.timedelta(days=1))

    def after_market_close_with_buffer(self, market_code: str, local_close_hhmm: str, buffer_minutes: int = 30) -> bool:
        now = self.now()
        hh, mm = map(int, local_close_hhmm.split(":"))
        close_dt = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        close_dt = close_dt + dt.timedelta(minutes=buffer_minutes)
        return now >= close_dt


def default_end_date_us_eastern_today() -> date:
    """US Eastern 기준 '오늘'을 기본 end date로 반환.
    FDR은 완결된 일봉만 반환하므로 당일 장중 데이터가 섞이지 않음."""
    try:
        from zoneinfo import ZoneInfo
        us_eastern = ZoneInfo("America/New_York")
        return datetime.now(us_eastern).date()
    except ImportError:
        try:
            import pytz
            us_eastern = pytz.timezone("America/New_York")
            return datetime.now(us_eastern).date()
        except ImportError:
            return datetime.now(timezone.utc).date()


def default_end_date_us_eastern_cutoff(cutoff_hhmm: str = "18:00") -> date:
    """US Eastern 기준 cutoff 시각으로 기본 end date를 결정.

    Rules:
    - now_et >= cutoff -> today
    - now_et < cutoff -> yesterday
    """
    try:
        hh, mm = map(int, cutoff_hhmm.split(":"))
        if not (0 <= hh <= 23 and 0 <= mm <= 59):
            raise ValueError
    except Exception:
        hh, mm = 18, 0

    try:
        from zoneinfo import ZoneInfo

        us_eastern = ZoneInfo("America/New_York")
        now_et = datetime.now(us_eastern)
    except ImportError:
        try:
            import pytz

            us_eastern = pytz.timezone("America/New_York")
            now_et = datetime.now(us_eastern)
        except ImportError:
            # 최후 fallback: UTC 기준으로 동일 규칙 적용
            now_et = datetime.now(timezone.utc)

    cutoff_dt = now_et.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if now_et >= cutoff_dt:
        return now_et.date()
    return (now_et - timedelta(days=1)).date()
