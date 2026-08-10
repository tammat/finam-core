from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


ZERO = Decimal("0")
HUNDRED = Decimal("100")


class CostModelV1(StrEnum):
    EQUITY_FIXED_PLUS_TURNOVER = (
        "EQUITY_FIXED_PLUS_TURNOVER"
    )
    FUTURES_MAKER_TAKER = (
        "FUTURES_MAKER_TAKER"
    )


@dataclass(frozen=True, slots=True)
class EconomicCostContractV1:
    model: CostModelV1

    commission_per_side: Decimal = ZERO
    commission_pct: Decimal = ZERO

    maker_rate_pct: Decimal = ZERO
    taker_rate_pct: Decimal = ZERO

    slippage_per_side: Decimal = ZERO
    spread_cost_per_side: Decimal = ZERO

    exchange_fee_per_side: Decimal = ZERO
    clearing_fee_per_side: Decimal = ZERO


@dataclass(frozen=True, slots=True)
class EconomicResolvedCostV1:
    commission: Decimal
    spread_cost: Decimal
    slippage: Decimal
    exchange_fee: Decimal
    clearing_fee: Decimal
    funding_cost: Decimal

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


def resolve_round_trip_cost_v1(
    *,
    entry_notional_rub: Decimal,
    exit_notional_rub: Decimal,
    contract: EconomicCostContractV1,
    entry_is_taker: bool = True,
    exit_is_taker: bool = True,
    funding_cost: Decimal = ZERO,
) -> EconomicResolvedCostV1:

    if entry_notional_rub < ZERO:
        raise ValueError(
            "entry_notional_rub must be >= 0"
        )

    if exit_notional_rub < ZERO:
        raise ValueError(
            "exit_notional_rub must be >= 0"
        )

    if funding_cost < ZERO:
        raise ValueError(
            "funding_cost must be >= 0"
        )

    if contract.model == (
        CostModelV1.EQUITY_FIXED_PLUS_TURNOVER
    ):
        commission = (
            contract.commission_per_side
            * Decimal("2")
            + (
                entry_notional_rub
                + exit_notional_rub
            )
            * contract.commission_pct
        )

    elif contract.model == (
        CostModelV1.FUTURES_MAKER_TAKER
    ):
        entry_rate_pct = (
            contract.taker_rate_pct
            if entry_is_taker
            else contract.maker_rate_pct
        )

        exit_rate_pct = (
            contract.taker_rate_pct
            if exit_is_taker
            else contract.maker_rate_pct
        )

        commission = (
            entry_notional_rub
            * entry_rate_pct
            / HUNDRED
            + exit_notional_rub
            * exit_rate_pct
            / HUNDRED
        )

    else:
        raise ValueError(
            f"unsupported cost model={contract.model}"
        )

    spread_cost = (
        contract.spread_cost_per_side
        * Decimal("2")
    )

    slippage = (
        contract.slippage_per_side
        * Decimal("2")
    )

    exchange_fee = (
        contract.exchange_fee_per_side
        * Decimal("2")
    )

    clearing_fee = (
        contract.clearing_fee_per_side
        * Decimal("2")
    )

    return EconomicResolvedCostV1(
        commission=commission,
        spread_cost=spread_cost,
        slippage=slippage,
        exchange_fee=exchange_fee,
        clearing_fee=clearing_fee,
        funding_cost=funding_cost,
    )
