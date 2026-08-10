from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from marketcore.research.economics.canonical_economic_gate_adapter_v1 import (
    CanonicalEconomicTradeInputV1,
)
from marketcore.research.economics.canonical_monetary_normalizer_v1 import (
    MonetaryContractV1,
    normalize_gross_pnl_rub_v1,
)
from marketcore.research.economics.economic_cost_resolver_v1 import (
    EconomicCostContractV1,
    resolve_round_trip_cost_v1,
)


@dataclass(frozen=True, slots=True)
class CanonicalReplayTradeV1:
    price_pnl: Decimal
    quantity: Decimal
    entry_price: Decimal
    exit_price: Decimal

    entry_is_taker: bool = True
    exit_is_taker: bool = True

    funding_cost: Decimal = Decimal("0")


def build_economic_trade_v1(
    *,
    trade: CanonicalReplayTradeV1,
    monetary_contract: MonetaryContractV1,
    cost_contract: EconomicCostContractV1,
) -> CanonicalEconomicTradeInputV1:

    gross_pnl_rub = normalize_gross_pnl_rub_v1(
        price_pnl=trade.price_pnl,
        quantity=trade.quantity,
        contract=monetary_contract,
    )

    if monetary_contract.asset_class.value == "EQUITY":
        entry_notional_rub = (
            trade.entry_price
            * trade.quantity
            * monetary_contract.lot_size
        )

        exit_notional_rub = (
            trade.exit_price
            * trade.quantity
            * monetary_contract.lot_size
        )

    else:
        # Для futures стоимость контракта:
        # price / tick_size * tick_value.
        entry_notional_rub = (
            trade.entry_price
            / monetary_contract.tick_size
            * monetary_contract.tick_value
            * trade.quantity
        )

        exit_notional_rub = (
            trade.exit_price
            / monetary_contract.tick_size
            * monetary_contract.tick_value
            * trade.quantity
        )

    cost = resolve_round_trip_cost_v1(
        entry_notional_rub=entry_notional_rub,
        exit_notional_rub=exit_notional_rub,
        contract=cost_contract,
        entry_is_taker=trade.entry_is_taker,
        exit_is_taker=trade.exit_is_taker,
        funding_cost=trade.funding_cost,
    )

    return CanonicalEconomicTradeInputV1(
        gross_pnl=gross_pnl_rub,
        commission=cost.commission,
        slippage=cost.slippage,
        spread_cost=cost.spread_cost,
        exchange_fee=cost.exchange_fee,
        clearing_fee=cost.clearing_fee,
        funding_cost=cost.funding_cost,
    )


def build_economic_trade_set_v1(
    *,
    trades: Iterable[CanonicalReplayTradeV1],
    monetary_contract: MonetaryContractV1,
    cost_contract: EconomicCostContractV1,
) -> tuple[CanonicalEconomicTradeInputV1, ...]:

    return tuple(
        build_economic_trade_v1(
            trade=trade,
            monetary_contract=monetary_contract,
            cost_contract=cost_contract,
        )
        for trade in trades
    )
