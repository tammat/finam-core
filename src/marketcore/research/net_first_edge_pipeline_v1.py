from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Callable

from marketcore.research.economics.canonical_economic_gate_adapter_v1 import (
    CanonicalEconomicTradeInputV1,
    evaluate_canonical_economic_gate_v1,
)
from marketcore.research.economics.economic_cost_gate_v1 import (
    EconomicCostGatePolicyV1,
    EconomicCostGateResultV1,
)


class NetFirstPipelineStatusV1(StrEnum):
    REJECT_ECONOMIC_GATE = "REJECT_ECONOMIC_GATE"
    ADMIT_ROBUSTNESS = "ADMIT_ROBUSTNESS"


@dataclass(frozen=True, slots=True)
class NetFirstPipelineResultV1:
    status: NetFirstPipelineStatusV1
    economic_result: EconomicCostGateResultV1
    robustness_called: bool


def evaluate_net_first_candidate_v1(
    *,
    economic_trades: tuple[
        CanonicalEconomicTradeInputV1,
        ...
    ],
    economic_policy: EconomicCostGatePolicyV1,
    robustness_runner: Callable[[], object] | None = None,
) -> NetFirstPipelineResultV1:

    economic_result = (
        evaluate_canonical_economic_gate_v1(
            economic_trades,
            economic_policy,
        )
    )

    if not economic_result.passed:
        return NetFirstPipelineResultV1(
            status=(
                NetFirstPipelineStatusV1
                .REJECT_ECONOMIC_GATE
            ),
            economic_result=economic_result,
            robustness_called=False,
        )

    if robustness_runner is not None:
        robustness_runner()

    return NetFirstPipelineResultV1(
        status=(
            NetFirstPipelineStatusV1
            .ADMIT_ROBUSTNESS
        ),
        economic_result=economic_result,
        robustness_called=(
            robustness_runner is not None
        ),
    )
