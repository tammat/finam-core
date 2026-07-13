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


@dataclass(frozen=True, slots=True)
class SignalFunnelStageV2:
    label: str
    count: int
    conversion: str
    status: str


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
