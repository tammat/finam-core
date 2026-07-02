from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ResearchViewModel:
    pipeline_status: str
    top3_status: str
    edge_factory_status: str
    research_candidates: int
    oos_pass: int
    paper_ready: int
    data_source: str
