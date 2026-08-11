from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

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


def build_verified_net_metrics_v1(
    net_values: Iterable[Decimal],
) -> VerifiedNetMetricsV1:
    rows = tuple(net_values)
    zero = Decimal("0")
    trade_count = len(rows)

    net_pnl = sum(rows, zero)

    net_expectancy = (
        net_pnl / Decimal(trade_count)
        if trade_count
        else zero
    )

    gross_profit = sum(
        (value for value in rows if value > zero),
        zero,
    )

    gross_loss = abs(
        sum(
            (value for value in rows if value < zero),
            zero,
        )
    )

    if gross_loss > zero:
        net_profit_factor = gross_profit / gross_loss
    elif gross_profit > zero:
        net_profit_factor = Decimal("Infinity")
    else:
        net_profit_factor = zero

    return VerifiedNetMetricsV1(
        trades=trade_count,
        net_profit_factor=net_profit_factor,
        net_expectancy=net_expectancy,
    )


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
