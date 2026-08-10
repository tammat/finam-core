from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from marketcore.research.economics.economic_cost_gate_v1 import (
    EconomicCostGatePolicyV1,
    EconomicGateStatusV1,
)


@dataclass(frozen=True, slots=True)
class VerifiedNetMetricsV1:
    trades: int
    net_profit_factor: Decimal
    net_expectancy: Decimal


@dataclass(frozen=True, slots=True)
class VerifiedNetAdmissionResultV1:
    status: EconomicGateStatusV1
    passed: bool


def evaluate_verified_net_admission_v1(
    *,
    metrics: VerifiedNetMetricsV1,
    policy: EconomicCostGatePolicyV1,
) -> VerifiedNetAdmissionResultV1:

    if metrics.trades < policy.minimum_trades:
        status = (
            EconomicGateStatusV1
            .REJECT_INSUFFICIENT_TRADES
        )

    elif (
        metrics.net_expectancy
        <= policy.minimum_net_expectancy
    ):
        status = (
            EconomicGateStatusV1
            .REJECT_NEGATIVE_EXPECTANCY
        )

    elif (
        metrics.net_profit_factor
        <= policy.minimum_net_profit_factor
    ):
        status = (
            EconomicGateStatusV1
            .REJECT_PROFIT_FACTOR
        )

    else:
        status = EconomicGateStatusV1.PASS

    return VerifiedNetAdmissionResultV1(
        status=status,
        passed=(
            status
            == EconomicGateStatusV1.PASS
        ),
    )
