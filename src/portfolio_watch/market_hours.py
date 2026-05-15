from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo


def is_weekday_market_time(
    now: datetime | None = None,
    timezone: str = "Asia/Taipei",
    start: time = time(9, 0),
    end: time = time(13, 30),
) -> bool:
    current = now.astimezone(ZoneInfo(timezone)) if now else datetime.now(ZoneInfo(timezone))
    if current.weekday() >= 5:
        return False

    return start <= current.time() <= end
