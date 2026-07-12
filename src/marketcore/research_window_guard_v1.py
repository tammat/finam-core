from __future__ import annotations

import os
from datetime import datetime, time
from zoneinfo import ZoneInfo


MOSCOW = ZoneInfo("Europe/Moscow")


def require_off_market_research_window(task_name: str) -> None:
    now = datetime.now(MOSCOW)
    override = os.getenv("MARKETCORE_ALLOW_MARKET_HOURS_RESEARCH") == "1"
    weekday = now.weekday() < 5
    protected_session = time(8, 45) <= now.time() <= time(23, 59, 59)
    if weekday and protected_session and not override:
        raise RuntimeError(
            f"OFF_MARKET_RESEARCH_WINDOW_REQUIRED:{task_name}:"
            f"now={now.isoformat(timespec='minutes')}:next_window=00:00-08:44_MSK"
        )
    if override:
        print(f"MARKET_HOURS_RESEARCH_OVERRIDE=1 task={task_name} now={now.isoformat(timespec='minutes')}")
    else:
        print(f"OFF_MARKET_RESEARCH_WINDOW_OK task={task_name} now={now.isoformat(timespec='minutes')}")
