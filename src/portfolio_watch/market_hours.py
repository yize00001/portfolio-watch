from __future__ import annotations

from datetime import date, datetime, time
from zoneinfo import ZoneInfo


def is_trading_day(d: date | None = None, timezone: str = "Asia/Taipei") -> bool:
    if d is None:
        d = datetime.now(ZoneInfo(timezone)).date()
    try:
        import exchange_calendars as xcals
        cal = xcals.get_calendar("XTAI")
        return cal.is_session(d.isoformat())
    except Exception:
        return d.weekday() < 5


def is_weekday_market_time(
    now: datetime | None = None,
    timezone: str = "Asia/Taipei",
    start: time = time(9, 0),
    end: time = time(13, 30),
) -> bool:
    current = now.astimezone(ZoneInfo(timezone)) if now else datetime.now(ZoneInfo(timezone))
    if not is_trading_day(current.date(), timezone):
        return False
    return start <= current.time() <= end
