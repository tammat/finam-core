from __future__ import annotations

from typing import Final

QUALITY_STATUSES: Final[tuple[str, ...]] = (
    "VALID",
    "WARNING",
    "REJECTED",
    "REVIEW_REQUIRED",
)

QUALITY_REASONS: Final[tuple[str, ...]] = (
    "BAD_TICK",
    "DUPLICATE_BAR",
    "UNKNOWN_SYMBOL",
    "SESSION_GAP",
    "ROLL_CONFLICT",
    "TIME_ORDER_VIOLATION",
    "MISSING_DATA",
    "STALE_DATA",
    "NORMALIZATION_ERROR",
)


def is_valid_quality_status(value: str) -> bool:
    return value in QUALITY_STATUSES


def sql_check_in(values: tuple[str, ...]) -> str:
    quoted = ",".join("'" + v.replace("'", "''") + "'" for v in values)
    return f"({quoted})"
