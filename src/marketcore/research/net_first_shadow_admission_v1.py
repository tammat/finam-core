from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from marketcore.research.economics.canonical_economic_gate_adapter_v1 import (
    CanonicalEconomicTradeInputV1,
    evaluate_canonical_economic_gate_v1,
)
from marketcore.research.economics.economic_cost_gate_v1 import (
    EconomicCostGatePolicyV1,
    EconomicCostGateResultV1,
)


class ShadowAdmissionDecisionV1(StrEnum):
    WOULD_REJECT = "WOULD_REJECT"
    WOULD_ADMIT = "WOULD_ADMIT"


@dataclass(frozen=True, slots=True)
class ShadowAdmissionResultV1:
    decision: ShadowAdmissionDecisionV1
    economic_result: EconomicCostGateResultV1

    # Shadow mode никогда не блокирует production flow.
    production_blocked: bool = False


def evaluate_shadow_admission_v1(
    *,
    economic_trades: tuple[
        CanonicalEconomicTradeInputV1,
        ...
    ],
    policy: EconomicCostGatePolicyV1,
) -> ShadowAdmissionResultV1:

    result = evaluate_canonical_economic_gate_v1(
        economic_trades,
        policy,
    )

    decision = (
        ShadowAdmissionDecisionV1.WOULD_ADMIT
        if result.passed
        else ShadowAdmissionDecisionV1.WOULD_REJECT
    )

    return ShadowAdmissionResultV1(
        decision=decision,
        economic_result=result,
        production_blocked=False,
    )
