from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True, slots=True)
class ProgramSnapshotV2:
    quarter_code: str
    platform_status: str
    research_status: str
    top3_status: str
    paper_status: str
    marketcore_status: str
    summary_refreshed_at: datetime | None
    readiness_total: int
    readiness_ready: int
    micro_live_allowed: int
    readiness_refreshed_at: datetime | None
    generated_at: datetime
