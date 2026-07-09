from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class PortfolioRowV1:
    source_view: str
    values: dict[str, Any]


@dataclass(frozen=True, slots=True)
class PortfolioSnapshotV1:
    summary: tuple[PortfolioRowV1, ...]
    positions: tuple[PortfolioRowV1, ...]
    dashboard: tuple[PortfolioRowV1, ...]
    visualization: tuple[PortfolioRowV1, ...]
