from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True, slots=True)
class ResearchAlgorithmResultV2:
    family: str
    markets: int
    variants: int
    best_folds: int
    folds_total: int
    best_profit_factor: float
    passes: int
    status: str

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
    edge_search_status: str
    edge_search_step: str
    edge_search_progress_pct: int
    edge_search_markets: int
    edge_search_combinations: int
    edge_search_pass: int
    edge_search_finished_at: datetime | None
    algorithm_results: tuple[ResearchAlgorithmResultV2, ...]
    generated_at: datetime
