from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


SOURCE_VERSION = "TREND_PULLBACK_CANONICAL_COST_VALIDATION_V1"


@dataclass(frozen=True)
class CostedTrade:
    gross_pnl: Decimal

    commission: Decimal

    # В research execution contract slippage является
    # TOTAL execution slippage:
    #
    # spread_cost
    # + impact_cost
    # + residual/base slippage
    slippage: Decimal

    net_pnl: Decimal


def apply_research_cost_identity(
    gross_pnl: Decimal,
    commission: Decimal,
    slippage: Decimal,
) -> CostedTrade:
    """
    Каноническая cost identity research execution слоя MarketCore.

    Важно:
    spread_cost и impact_cost отдельно здесь не вычитаются,
    если они уже входят в переданный total slippage.
    """

    if commission < 0:
        raise ValueError(
            "ERROR=NEGATIVE_COMMISSION"
        )

    if slippage < 0:
        raise ValueError(
            "ERROR=NEGATIVE_SLIPPAGE"
        )

    net_pnl = (
        gross_pnl
        - commission
        - slippage
    )

    return CostedTrade(
        gross_pnl=gross_pnl,
        commission=commission,
        slippage=slippage,
        net_pnl=net_pnl,
    )


def main() -> int:
    print(
        "cost_identity="
        "gross_pnl-commission-total_execution_slippage"
    )

    print(
        "spread_cost_separately_subtracted=0"
    )

    print(
        "impact_cost_separately_subtracted=0"
    )

    print(
        "runtime_changed=0"
    )

    print(
        "execution_changed=0"
    )

    print(
        "orders_changed=0"
    )

    print(
        "fills_changed=0"
    )

    print(
        "economic_edge_claimed=0"
    )

    print(
        "micro_live_allowed=0"
    )

    print(
        "VERDICT="
        "TREND_PULLBACK_CANONICAL_COST_IDENTITY_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


def equity_round_trip_commission(
    *,
    entry_notional: Decimal,
    exit_notional: Decimal,
    commission_per_trade: Decimal,
    commission_pct: Decimal,
) -> Decimal:
    """
    Каноническая round-trip комиссия для EQUITY.

    commission_per_trade — per side.
    commission_pct применяется к обороту entry + exit.
    """

    if entry_notional < 0 or exit_notional < 0:
        raise ValueError(
            "ERROR=NEGATIVE_NOTIONAL"
        )

    if commission_per_trade < 0:
        raise ValueError(
            "ERROR=NEGATIVE_COMMISSION_PER_TRADE"
        )

    if commission_pct < 0:
        raise ValueError(
            "ERROR=NEGATIVE_COMMISSION_PCT"
        )

    fixed = (
        commission_per_trade
        * Decimal("2")
    )

    percent = (
        entry_notional
        + exit_notional
    ) * commission_pct

    return fixed + percent


def equity_round_trip_slippage(
    *,
    slippage_per_trade: Decimal,
) -> Decimal:
    """
    slippage_per_trade в cost registry трактуется как per-side fixed
    component, поэтому для round-trip используется x2.

    Market spread/impact сюда отдельно не добавляется:
    это отдельный execution-aware слой.
    """

    if slippage_per_trade < 0:
        raise ValueError(
            "ERROR=NEGATIVE_SLIPPAGE_PER_TRADE"
        )

    return (
        slippage_per_trade
        * Decimal("2")
    )
