from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProfitViewModel:
    production_edges: int
    paper_edges: int
    shadow_edges: int
    research_candidates: int
    paper_status: str
    shadow_status: str
    data_source: str
