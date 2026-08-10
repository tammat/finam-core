from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from decimal import Decimal


class EconomicEvidenceClassV1(StrEnum):
    VERIFIED_NET_METRICS = "VERIFIED_NET_METRICS"
    COST_AWARE_PROMOTED_METRICS = "COST_AWARE_PROMOTED_METRICS"
    REPLAY_REQUIRED = "REPLAY_REQUIRED"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass(frozen=True, slots=True)
class EconomicEvidenceDecisionV1:
    evidence_class: EconomicEvidenceClassV1
    direct_gate_allowed: bool
    replay_required: bool
    reason_code: str


def classify_economic_evidence_v1(
    *,
    runner_version: str,
    score_formula_version: str,
    source_version: str,
    verdict_code: str,
    commission: Decimal,
    slippage: Decimal,
) -> EconomicEvidenceDecisionV1:

    if (
        runner_version == "POSTGRESQL_EDGE_BACKTEST_ADAPTER_V1"
        and score_formula_version == "EDGE_RESEARCH_METRICS_V1"
        and source_version == "POSTGRESQL_EDGE_BACKTEST_ADAPTER_V1"
        and verdict_code == "POSITIVE_AFTER_COSTS"
        and (commission > 0 or slippage > 0)
    ):
        return EconomicEvidenceDecisionV1(
            evidence_class=(
                EconomicEvidenceClassV1.VERIFIED_NET_METRICS
            ),
            direct_gate_allowed=True,
            replay_required=False,
            reason_code="POSTGRESQL_AFTER_COST_METRICS",
        )

    if (
        runner_version == "REGIME_AWARE_EDGE_DISCOVERY_V2"
        and score_formula_version == "REGIME_COST_ADJUSTED_OOS_V2"
        and source_version == "REGIME_OOS_CANONICAL_PROMOTION_V1"
    ):
        return EconomicEvidenceDecisionV1(
            evidence_class=(
                EconomicEvidenceClassV1.COST_AWARE_PROMOTED_METRICS
            ),
            direct_gate_allowed=True,
            replay_required=False,
            reason_code="REGIME_COST_ADJUSTED_OOS",
        )

    if runner_version in (
        "STRATEGY_EXECUTION_RUNNER_V1",
        "STRATEGY_EXECUTION_RUNNER_V2",
    ):
        return EconomicEvidenceDecisionV1(
            evidence_class=(
                EconomicEvidenceClassV1.REPLAY_REQUIRED
            ),
            direct_gate_allowed=False,
            replay_required=True,
            reason_code="ZERO_COST_OBSERVATION_NOT_NET_VERIFIED",
        )

    return EconomicEvidenceDecisionV1(
        evidence_class=EconomicEvidenceClassV1.UNSUPPORTED,
        direct_gate_allowed=False,
        replay_required=True,
        reason_code="UNKNOWN_ECONOMIC_SEMANTICS",
    )
