from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from marketcore.normalization.dto import CanonicalMarketBarDTO


@dataclass
class NormalizationContext:
    raw: CanonicalMarketBarDTO
    normalization_run_id: int | None = None

    source_system_id: int | None = None
    source_system: dict[str, Any] | None = None
    symbol_alias_id: int | None = None
    symbol_alias: dict[str, Any] | None = None
    instrument_id: int | None = None
    instrument: dict[str, Any] | None = None
    contract_id: int | None = None
    contract: dict[str, Any] | None = None
    timeframe_id: int | None = None
    timeframe: dict[str, Any] | None = None
    event_type_id: int | None = None
    quality_status_id: int | None = None

    event_uuid: str | None = None
    quality_events: list[dict[str, Any]] = field(default_factory=list)
    lineage_edges: list[dict[str, Any]] = field(default_factory=list)
    metrics: dict[str, int] = field(default_factory=dict)

    rejected: bool = False
    rejection_reason: str | None = None

    def reject(self, reason: str) -> None:
        self.rejected = True
        self.rejection_reason = reason
        self.metrics["rows_rejected"] = self.metrics.get("rows_rejected", 0) + 1

    def add_quality_event(self, event: dict[str, Any]) -> None:
        self.quality_events.append(event)

    def add_lineage_edge(self, edge: dict[str, Any]) -> None:
        self.lineage_edges.append(edge)

    def increment(self, key: str, value: int = 1) -> None:
        self.metrics[key] = self.metrics.get(key, 0) + value
