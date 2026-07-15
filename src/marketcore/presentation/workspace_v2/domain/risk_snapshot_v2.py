from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class RiskClusterSnapshotV2:
    cluster_code: str
    total_positions: int
    total_heat: Decimal
    portfolio_share: Decimal
    risk_state_code: str
    calculated_at: datetime


@dataclass(frozen=True, slots=True)
class RiskPermissionSnapshotV2:
    runtime_allowed: bool
    execution_allowed: bool
    micro_live_allowed: bool
    daily_risk_ratio: Decimal
    refreshed_at: datetime


@dataclass(frozen=True, slots=True)
class RiskDecisionAggregateV2:
    decisions_total: int
    blocked_total: int
    average_risk_score: Decimal | None
    average_position_score: Decimal | None
    average_exposure_score: Decimal | None
    average_daily_loss_score: Decimal | None
    average_correlation_score: Decimal | None
    refreshed_at: datetime | None


@dataclass(frozen=True, slots=True)
class RiskSnapshotV2:
    clusters: tuple[RiskClusterSnapshotV2, ...]
    permissions: RiskPermissionSnapshotV2 | None
    decisions: RiskDecisionAggregateV2
    maximum_age_seconds: int
    generated_at: datetime
    portfolio_freshness_code: str
    permission_freshness_code: str
    decision_freshness_code: str
