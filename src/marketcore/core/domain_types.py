from __future__ import annotations

from typing import Final


CATALOG: Final[str] = "CATALOG"
FEATURE: Final[str] = "FEATURE"
MODEL: Final[str] = "MODEL"
EXPERIMENT: Final[str] = "EXPERIMENT"
CANDIDATE: Final[str] = "CANDIDATE"
PAPER: Final[str] = "PAPER"
RUNTIME: Final[str] = "RUNTIME"
TRADE: Final[str] = "TRADE"
RISK_EVENT: Final[str] = "RISK_EVENT"
REPORT: Final[str] = "REPORT"

CANONICAL_DOMAIN_TYPES: Final[tuple[str, ...]] = (
    CATALOG,
    FEATURE,
    MODEL,
    EXPERIMENT,
    CANDIDATE,
    PAPER,
    RUNTIME,
    TRADE,
    RISK_EVENT,
    REPORT,
)

ACTIVE_KG_DOMAIN_TYPES_V1: Final[tuple[str, ...]] = (
    CATALOG,
    FEATURE,
    MODEL,
    EXPERIMENT,
)


def is_canonical_domain_type(value: str) -> bool:
    return value in CANONICAL_DOMAIN_TYPES


def normalize_domain_type(value: str) -> str:
    normalized = value.strip().upper()

    aliases = {
        "CATALOG_OBJECT": CATALOG,
        "CATALOG_ITEM": CATALOG,
        "FEATURES": FEATURE,
        "MODELS": MODEL,
        "EXPERIMENTS": EXPERIMENT,
        "PAPER_SESSION": PAPER,
        "RUNTIME_SIGNAL": RUNTIME,
    }

    return aliases.get(normalized, normalized)


def require_canonical_domain_type(value: str) -> str:
    normalized = normalize_domain_type(value)
    if not is_canonical_domain_type(normalized):
        raise ValueError(f"Unknown domain type: {value}")
    return normalized
