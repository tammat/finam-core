#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

SUPPORTED_TIMEZONES = (
    "Europe/Moscow",
    "Europe/Helsinki",
    "UTC",
)

DEFAULT_TIMEZONE = "Europe/Moscow"

def normalize_timezone(value: str | None) -> str:
    if value in SUPPORTED_TIMEZONES:
        return value
    return DEFAULT_TIMEZONE

def convert_utc_iso(value: str, timezone_name: str | None = None) -> str:
    tz = ZoneInfo(normalize_timezone(timezone_name))

    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))

    return dt.astimezone(tz).isoformat()
