from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ControlCenterTrafficLightV2:
    code: str
    label: str
    detail: str
    status: str
    target: str
    detail_key: str = ""
    detail_args: tuple[tuple[str, Any], ...] = ()


@dataclass(frozen=True, slots=True)
class RelationshipCandidateV2:
    family: str
    source: str
    target: str
    regime: str
    session: str
    oos_trades: int
    profit_factor: float
    expectancy_bps: float
    coverage_pct: float
    verdict: str
    status: str
    family_code: str = "UNKNOWN"
    regime_code: str = "ALL"
    session_code: str = "ALL"
    verdict_code: str = "UNVERIFIED"


@dataclass(frozen=True, slots=True)
class SignalFunnelStageV2:
    label: str
    count: int
    conversion: str
    status: str
    stage_code: str = "UNKNOWN"
    pass_rate_pct: float | None = None
    source_identity: str = ""
    source_as_of: Any = None
    freshness_code: str = "UNAVAILABLE"
    quality_code: str = "UNVERIFIED"
    reason_code: str = ""
    net_pnl: Any = None
    cost_impact: Any = None


@dataclass(frozen=True, slots=True)
class SignalLossReasonV2:
    code: str
    label: str
    count: int
    action: str
    status: str
    action_target: str


@dataclass(frozen=True, slots=True)
class ControlCenterV2ViewModel:
    title: str
    subtitle: str
    traffic_lights: tuple[ControlCenterTrafficLightV2, ...]
    relationship_summary: dict[str, Any]
    relationships: tuple[RelationshipCandidateV2, ...]
    funnel_stages: tuple[SignalFunnelStageV2, ...]
    loss_reasons: tuple[SignalLossReasonV2, ...]
    funnel_comparable: bool
    shadow_summary: dict[str, Any]
    execution_quality: tuple[dict[str, Any], ...]
    execution_variants: tuple[dict[str, Any], ...]
    volatility_analysis: tuple[dict[str, Any], ...]
    risk_analysis: tuple[dict[str, Any], ...]
    entry_analysis: tuple[dict[str, Any], ...]
    market_prerequisites: tuple[dict[str, Any], ...]
    exit_analysis: tuple[dict[str, Any], ...]
    block_analysis: tuple[dict[str, Any], ...]
    shadow_requirements: tuple[dict[str, Any], ...]
    shadow_process: tuple[dict[str, Any], ...]
    shadow_alerts: tuple[dict[str, Any], ...]
    forward_blockers: tuple[dict[str, Any], ...]
    forward_pass_process: tuple[dict[str, Any], ...]
    forward_readiness: tuple[dict[str, Any], ...]
    edge_search_process: tuple[dict[str, Any], ...]
    edge_search_results: tuple[dict[str, Any], ...]
    swing_summary: dict[str, Any]
