from __future__ import annotations

import os
from datetime import datetime, time
from zoneinfo import ZoneInfo


MOSCOW = ZoneInfo("Europe/Moscow")
DEFAULT_OPENING_GUARD_START = time(5, 0)
DEFAULT_OPENING_GUARD_END = time(9, 15)


def _configured_time(name: str, default: time) -> time:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        hour, minute = (int(part) for part in raw.split(":", 1))
        return time(hour, minute)
    except (TypeError, ValueError):
        return default


def is_market_opening_guard(now: datetime | None = None) -> bool:
    """Protect the host while preflight and the first market bars are forming."""
    local = (now or datetime.now(MOSCOW)).astimezone(MOSCOW)
    if local.weekday() >= 5:
        return False
    start = _configured_time("MARKETCORE_OPENING_GUARD_START", DEFAULT_OPENING_GUARD_START)
    end = _configured_time("MARKETCORE_OPENING_GUARD_END", DEFAULT_OPENING_GUARD_END)
    return start <= local.time().replace(tzinfo=None) <= end


def require_off_market_research_window(task_name: str) -> None:
    now = datetime.now(MOSCOW)
    override = os.getenv("MARKETCORE_ALLOW_MARKET_HOURS_RESEARCH") == "1"
    weekday = now.weekday() < 5
    protected_session = (
        is_market_opening_guard(now)
        or time(8, 45) <= now.time() <= time(23, 59, 59)
    )
    if weekday and protected_session and not override:
        raise RuntimeError(
            f"OFF_MARKET_RESEARCH_WINDOW_REQUIRED:{task_name}:"
            f"now={now.isoformat(timespec='minutes')}:next_window=00:00-04:59_MSK"
        )
    if override:
        print(f"MARKET_HOURS_RESEARCH_OVERRIDE=1 task={task_name} now={now.isoformat(timespec='minutes')}")
    else:
        print(f"OFF_MARKET_RESEARCH_WINDOW_OK task={task_name} now={now.isoformat(timespec='minutes')}")
