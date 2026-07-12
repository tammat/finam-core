from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo


class DateTimeService:
    def format_datetime(self, value, timezone: str = "Europe/Moscow") -> str:
        if not value:
            return "—"

        try:
            if isinstance(value, str):
                dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            elif isinstance(value, datetime):
                dt = value
            else:
                return "—"

            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=ZoneInfo("UTC"))

            return dt.astimezone(ZoneInfo(timezone)).strftime("%d.%m.%Y, %H:%M")
        except Exception:
            return str(value)
