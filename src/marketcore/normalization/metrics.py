from __future__ import annotations

from dataclasses import dataclass


@dataclass
class NormalizationMetrics:
    rows_total: int = 0
    rows_new: int = 0
    rows_updated: int = 0
    rows_rejected: int = 0
    quality_events: int = 0
    lineage_edges: int = 0
    duration_ms: int = 0
