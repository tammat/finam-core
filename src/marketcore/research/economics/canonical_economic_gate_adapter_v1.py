from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from marketcore.research.economics.economic_cost_gate_v1 import (
    EconomicCostGatePolicyV1,
    EconomicCostGateResultV1,
    EconomicTradeV1,
    evaluate_economic_cost_gate_v1,
)


ZERO = Decimal("0")


@dataclass(frozen=True, slots=True)
class CanonicalEconomicTradeInputV1:
    gross_pnl: Decimal
    commission: Decimal
    slippage: Decimal

    spread_cost: Decimal = ZERO
    exchange_fee: Decimal = ZERO
    clearing_fee: Decimal = ZERO
    funding_cost: Decimal = ZERO


def adapt_canonical_trade_v1(
    trade: CanonicalEconomicTradeInputV1,
) -> EconomicTradeV1:
    return EconomicTradeV1(
        gross_pnl=trade.gross_pnl,
        commission=trade.commission,
        spread_cost=trade.spread_cost,
        slippage=trade.slippage,
        exchange_fee=trade.exchange_fee,
        clearing_fee=trade.clearing_fee,
        funding_cost=trade.funding_cost,
    )


def evaluate_canonical_economic_gate_v1(
    trades: Iterable[
        CanonicalEconomicTradeInputV1
    ],
    policy: EconomicCostGatePolicyV1,
) -> EconomicCostGateResultV1:
    economic_trades = tuple(
        adapt_canonical_trade_v1(trade)
        for trade in trades
    )

    return evaluate_economic_cost_gate_v1(
        economic_trades,
        policy,
    )
