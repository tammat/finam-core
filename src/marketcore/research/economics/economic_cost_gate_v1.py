from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Iterable


ZERO = Decimal("0")
ONE = Decimal("1")


class EconomicGateStatusV1(StrEnum):
    PASS = "PASS"
    REJECT_NEGATIVE_EXPECTANCY = "REJECT_NEGATIVE_EXPECTANCY"
    REJECT_PROFIT_FACTOR = "REJECT_PROFIT_FACTOR"
    REJECT_INSUFFICIENT_TRADES = "REJECT_INSUFFICIENT_TRADES"
    REJECT_INVALID_COST = "REJECT_INVALID_COST"


@dataclass(frozen=True, slots=True)
class EconomicTradeV1:
    gross_pnl: Decimal
    commission: Decimal
    spread_cost: Decimal
    slippage: Decimal
    exchange_fee: Decimal = ZERO
    clearing_fee: Decimal = ZERO
    funding_cost: Decimal = ZERO

    @property
    def total_cost(self) -> Decimal:
        return (
            self.commission
            + self.spread_cost
            + self.slippage
            + self.exchange_fee
            + self.clearing_fee
            + self.funding_cost
        )

    @property
    def net_pnl(self) -> Decimal:
        return self.gross_pnl - self.total_cost


@dataclass(frozen=True, slots=True)
class EconomicCostGatePolicyV1:
    minimum_trades: int
    minimum_net_expectancy: Decimal
    minimum_net_profit_factor: Decimal


@dataclass(frozen=True, slots=True)
class EconomicCostGateResultV1:
    status: EconomicGateStatusV1

    trades: int

    gross_pnl: Decimal
    total_cost: Decimal
    net_pnl: Decimal

    net_expectancy: Decimal
    net_profit_factor: Decimal

    cost_to_gross_ratio: Decimal | None

    wins: int
    losses: int

    passed: bool


def evaluate_economic_cost_gate_v1(
    trades: Iterable[EconomicTradeV1],
    policy: EconomicCostGatePolicyV1,
) -> EconomicCostGateResultV1:

    rows = tuple(trades)

    if policy.minimum_trades < 1:
        raise ValueError(
            "minimum_trades must be >= 1"
        )

    for trade in rows:
        if trade.total_cost < ZERO:
            return EconomicCostGateResultV1(
                status=(
                    EconomicGateStatusV1
                    .REJECT_INVALID_COST
                ),
                trades=len(rows),
                gross_pnl=ZERO,
                total_cost=ZERO,
                net_pnl=ZERO,
                net_expectancy=ZERO,
                net_profit_factor=ZERO,
                cost_to_gross_ratio=None,
                wins=0,
                losses=0,
                passed=False,
            )

    gross_pnl = sum(
        (trade.gross_pnl for trade in rows),
        ZERO,
    )

    total_cost = sum(
        (trade.total_cost for trade in rows),
        ZERO,
    )

    net_values = tuple(
        trade.net_pnl
        for trade in rows
    )

    net_pnl = sum(
        net_values,
        ZERO,
    )

    trade_count = len(rows)

    net_expectancy = (
        net_pnl / Decimal(trade_count)
        if trade_count
        else ZERO
    )

    profits = tuple(
        value
        for value in net_values
        if value > ZERO
    )

    losses = tuple(
        value
        for value in net_values
        if value < ZERO
    )

    gross_profit = sum(
        profits,
        ZERO,
    )

    gross_loss = abs(
        sum(
            losses,
            ZERO,
        )
    )

    if gross_loss > ZERO:
        net_profit_factor = (
            gross_profit / gross_loss
        )
    elif gross_profit > ZERO:
        net_profit_factor = Decimal("Infinity")
    else:
        net_profit_factor = ZERO

    gross_abs = abs(gross_pnl)

    cost_to_gross_ratio = (
        total_cost / gross_abs
        if gross_abs > ZERO
        else None
    )

    if trade_count < policy.minimum_trades:
        status = (
            EconomicGateStatusV1
            .REJECT_INSUFFICIENT_TRADES
        )

    elif (
        net_expectancy
        <= policy.minimum_net_expectancy
    ):
        status = (
            EconomicGateStatusV1
            .REJECT_NEGATIVE_EXPECTANCY
        )

    elif (
        net_profit_factor
        <= policy.minimum_net_profit_factor
    ):
        status = (
            EconomicGateStatusV1
            .REJECT_PROFIT_FACTOR
        )

    else:
        status = EconomicGateStatusV1.PASS

    return EconomicCostGateResultV1(
        status=status,
        trades=trade_count,
        gross_pnl=gross_pnl,
        total_cost=total_cost,
        net_pnl=net_pnl,
        net_expectancy=net_expectancy,
        net_profit_factor=net_profit_factor,
        cost_to_gross_ratio=cost_to_gross_ratio,
        wins=len(profits),
        losses=len(losses),
        passed=(
            status
            == EconomicGateStatusV1.PASS
        ),
    )
