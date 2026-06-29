from __future__ import annotations

from typing import Final

REGISTRY_STATUSES: Final[tuple[str, ...]] = (
    "DISCOVERED",
    "REGISTERED",
    "VALIDATED",
    "APPROVED",
    "DEPRECATED",
    "ARCHIVED",
)

REGISTRY_MATURITY_LEVELS: Final[tuple[str, ...]] = (
    "RESEARCH",
    "VALIDATED",
    "SHADOW",
    "PAPER",
    "LIVE",
)


def is_valid_status(value: str) -> bool:
    return value in REGISTRY_STATUSES


def is_valid_maturity(value: str) -> bool:
    return value in REGISTRY_MATURITY_LEVELS


def sql_check_in(values: tuple[str, ...]) -> str:
    quoted = ",".join("'" + v.replace("'", "''") + "'" for v in values)
    return f"({quoted})"
