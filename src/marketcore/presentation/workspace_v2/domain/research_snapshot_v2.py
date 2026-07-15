from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True, slots=True)
class ResearchSnapshotV2:
    supervisor_status: str
    active_symbols: int
    failed_symbols: int
    last_cycle_at: datetime | None
    candidates: int
    oos_pass: int
    paper_ready: int
    summary_refreshed_at: datetime | None
    queue_total: int
    queue_pending: int
    queue_failed: int
    queue_updated_at: datetime | None
    oos_total: int
    oos_pass_total: int
    oos_updated_at: datetime | None
    generated_at: datetime
