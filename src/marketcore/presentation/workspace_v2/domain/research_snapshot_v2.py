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
    fail_reason: str

@dataclass(frozen=True, slots=True)
class MethodologyGateFailureV1:
    gate_code: str
    total: int
    failed: int
    passed: int
    fail_pct: float
    status: str

@dataclass(frozen=True, slots=True)
class ResearchUniverseItemV1:
    symbol: str
    category_code: str
    bars: int
    category_rank: int
    selected: bool
    reason_code: str
    process_id: str | None
    status: str
    progress_pct: float
    current_step: str

@dataclass(frozen=True, slots=True)
class InstrumentScoutItemV1:
    symbol: str
    category_code: str
    bars: int
    research_score: float
    decision_code: str
    reason_code: str
    next_action_code: str

@dataclass(frozen=True, slots=True)
class FuturesRollItemV1:
    root_symbol: str
    current_symbol: str
    next_symbol: str
    selected_symbol: str
    days_to_expiry: int
    current_volume: float
    next_volume: float
    progress_pct: float
    decision_code: str
    status_code: str
    max_leverage: float
    max_position_pct: float
    margin_source: str

@dataclass(frozen=True, slots=True)
class EdgeSearchRunAuditV1:
    process_id: str
    run_id: str
    status: str
    progress_pct: float
    current_step: str
    steps_completed: int
    steps_total: int
    duration_seconds: int
    outcome: str
    reason: str
    recommendation: str
    explanation: str
    started_at: datetime | None
    available_actions: tuple[dict[str, str], ...]

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
    next_plan_items: int
    next_plan_variants: int
    edge_auto_queue: int
    edge_auto_status: str
    scout_discovered: int
    scout_selected: int
    scout_backfill: int
    scout_watch_added: int
    scout_status: str
    methodology_evaluated: int
    methodology_pass: int
    execution_quote_symbols: int
    execution_spec_count: int
    execution_quote_status: str
    execution_spec_status: str
    methodology_failures: tuple[MethodologyGateFailureV1, ...]
    futures_roll_items: tuple[FuturesRollItemV1, ...]
    scout_items: tuple[InstrumentScoutItemV1, ...]
    universe_items: tuple[ResearchUniverseItemV1, ...]
    algorithm_results: tuple[ResearchAlgorithmResultV2, ...]
    edge_search_runs: tuple[EdgeSearchRunAuditV1, ...]
    generated_at: datetime
