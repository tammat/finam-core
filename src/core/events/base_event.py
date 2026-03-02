from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4


UTC = timezone.utc


def ensure_utc(ts: datetime | None) -> datetime:
    """
    Normalize timestamp to timezone-aware UTC.
    If naive datetime is provided — treat it as UTC.
    """
    if ts is None:
        return datetime.now(UTC)

    if ts.tzinfo is None:
        return ts.replace(tzinfo=UTC)

    return ts.astimezone(UTC)


class BaseEvent:
    def __init__(self, event_id: str | None = None, timestamp: datetime | None = None):
        self.event_id = event_id or str(uuid4())
        self.timestamp = ensure_utc(timestamp)