# src/core/time.py
from __future__ import annotations

from datetime import datetime, timezone

UTC = timezone.utc

def utcnow() -> datetime:
    """Timezone-aware UTC timestamp."""
    return datetime.now(UTC)