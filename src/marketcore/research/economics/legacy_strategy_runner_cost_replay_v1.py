from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


ZERO = Decimal("0")


@dataclass(frozen=True, slots=True)
class LegacyStrategyRunnerCostContractV1:
    commission_per_trade: Decimal
    commission_pct: Decimal
    slippage_per_trade: Decimal


@dataclass(frozen=True, slots=True)
class LegacyStrategyRunnerResolvedCostV1:
    commission: Decimal
    slippage: Decimal

    @property
    def total_cost(self) -> Decimal:
        return self.commission + self.slippage


def resolve_legacy_strategy_runner_cost_v1(
    *,
    entry_price: Decimal,
    contract: LegacyStrategyRunnerCostContractV1,
) -> LegacyStrategyRunnerResolvedCostV1:

    if entry_price < ZERO:
        raise ValueError(
            "entry_price must be >= 0"
        )

    commission = (
        contract.commission_per_trade
        + entry_price * contract.commission_pct
    )

    slippage = contract.slippage_per_trade

    return LegacyStrategyRunnerResolvedCostV1(
        commission=commission,
        slippage=slippage,
    )
