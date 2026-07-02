from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProgramViewModel:
    quarter: str
    platform_status: str
    research_status: str
    top3_status: str
    paper_status: str
    marketcore_status: str
    data_source: str
