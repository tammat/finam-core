from __future__ import annotations

from typing import Final

EVENT_LIFECYCLE_STATUSES: Final[tuple[str, ...]] = (
    "RECEIVED",
    "NORMALIZED",
    "VALIDATED",
    "PUBLISHED",
    "ARCHIVED",
)


def is_valid_event_lifecycle(value: str) -> bool:
    return value in EVENT_LIFECYCLE_STATUSES
