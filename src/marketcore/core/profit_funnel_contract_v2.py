from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from types import MappingProxyType
from typing import Mapping


class ProfitFunnelStageV2(str, Enum):
    RESEARCH = "RESEARCH"
    CANDIDATE = "CANDIDATE"
    VALIDATED_EDGE = "VALIDATED_EDGE"
    OOS = "OOS"
    FORWARD = "FORWARD"
    SHADOW = "SHADOW"
    PAPER = "PAPER"
    RUNTIME = "RUNTIME"
    LIVE = "LIVE"
    PROFIT = "PROFIT"


class ProfitFunnelDataScopeV2(str, Enum):
    REAL = "REAL"
    TEST = "TEST"


class ProfitFunnelFreshnessV2(str, Enum):
    CURRENT = "CURRENT"
    STALE = "STALE"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class ProfitFunnelStageMetricV2:
    stage: ProfitFunnelStageV2
    cohort_id: str
    data_scope: ProfitFunnelDataScopeV2
    count: int
    previous_count: int | None
    conversion_ratio: Decimal | None
    latency_seconds: int | None
    freshness: ProfitFunnelFreshnessV2
    rejection_reasons: Mapping[str, int]
    net_pnl: Decimal | None
    cost_impact: Decimal | None
    risk_impact: Decimal | None
    source_identity: str
    source_as_of: datetime | None
    observed_at: datetime
    quality_code: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "rejection_reasons", MappingProxyType(dict(self.rejection_reasons)))


@dataclass(frozen=True, slots=True)
class ProfitFunnelSnapshotV2:
    cohort_id: str
    data_scope: ProfitFunnelDataScopeV2
    generated_at: datetime
    stages: tuple[ProfitFunnelStageMetricV2, ...]


class ProfitFunnelContractErrorV2(ValueError):
    pass


def _aware(value: datetime | None, code: str) -> None:
    if value is None or value.tzinfo is None or value.utcoffset() is None:
        raise ProfitFunnelContractErrorV2(code)


def validate_profit_funnel_stage_v2(metric: ProfitFunnelStageMetricV2) -> ProfitFunnelStageMetricV2:
    if not metric.cohort_id.strip():
        raise ProfitFunnelContractErrorV2("PROFIT_FUNNEL_COHORT_REQUIRED")
    if metric.count < 0 or (metric.previous_count is not None and metric.previous_count < 0):
        raise ProfitFunnelContractErrorV2("PROFIT_FUNNEL_COUNT_INVALID")
    if metric.conversion_ratio is not None and metric.conversion_ratio < 0:
        raise ProfitFunnelContractErrorV2("PROFIT_FUNNEL_CONVERSION_INVALID")
    if metric.latency_seconds is not None and metric.latency_seconds < 0:
        raise ProfitFunnelContractErrorV2("PROFIT_FUNNEL_LATENCY_INVALID")
    if any(not str(code).strip() or count < 0 for code, count in metric.rejection_reasons.items()):
        raise ProfitFunnelContractErrorV2("PROFIT_FUNNEL_REJECTION_REASON_INVALID")
    if not metric.source_identity.strip():
        raise ProfitFunnelContractErrorV2("PROFIT_FUNNEL_SOURCE_REQUIRED")
    _aware(metric.observed_at, "PROFIT_FUNNEL_OBSERVED_AT_INVALID")
    if metric.freshness is ProfitFunnelFreshnessV2.UNAVAILABLE:
        if metric.source_as_of is not None:
            raise ProfitFunnelContractErrorV2("PROFIT_FUNNEL_UNAVAILABLE_SOURCE_TIME_FORBIDDEN")
    else:
        _aware(metric.source_as_of, "PROFIT_FUNNEL_SOURCE_AS_OF_REQUIRED")
    if metric.freshness is not ProfitFunnelFreshnessV2.CURRENT and metric.quality_code == "VERIFIED":
        raise ProfitFunnelContractErrorV2("PROFIT_FUNNEL_STALE_VERIFIED_FORBIDDEN")
    return metric


def validate_profit_funnel_snapshot_v2(snapshot: ProfitFunnelSnapshotV2) -> ProfitFunnelSnapshotV2:
    if not snapshot.cohort_id.strip():
        raise ProfitFunnelContractErrorV2("PROFIT_FUNNEL_COHORT_REQUIRED")
    _aware(snapshot.generated_at, "PROFIT_FUNNEL_GENERATED_AT_INVALID")
    expected = tuple(ProfitFunnelStageV2)
    actual = tuple(metric.stage for metric in snapshot.stages)
    if actual != expected:
        raise ProfitFunnelContractErrorV2("PROFIT_FUNNEL_STAGE_SEQUENCE_INVALID")
    for index, metric in enumerate(snapshot.stages):
        validate_profit_funnel_stage_v2(metric)
        if metric.cohort_id != snapshot.cohort_id:
            raise ProfitFunnelContractErrorV2("PROFIT_FUNNEL_COHORT_MISMATCH")
        if metric.data_scope is not snapshot.data_scope:
            raise ProfitFunnelContractErrorV2("PROFIT_FUNNEL_SCOPE_MISMATCH")
        if index == 0 and (metric.previous_count is not None or metric.conversion_ratio is not None):
            raise ProfitFunnelContractErrorV2("PROFIT_FUNNEL_INITIAL_CONVERSION_FORBIDDEN")
        if index > 0 and metric.previous_count != snapshot.stages[index - 1].count:
            raise ProfitFunnelContractErrorV2("PROFIT_FUNNEL_PREVIOUS_COUNT_MISMATCH")
    return snapshot
