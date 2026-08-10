from __future__ import annotations

from decimal import Decimal

from marketcore.research.economics.canonical_economic_gate_adapter_v1 import (
    CanonicalEconomicTradeInputV1,
    evaluate_canonical_economic_gate_v1,
)
from marketcore.research.economics.economic_cost_gate_v1 import (
    EconomicCostGatePolicyV1,
    EconomicGateStatusV1,
)


D = Decimal


POLICY = EconomicCostGatePolicyV1(
    minimum_trades=50,
    minimum_net_expectancy=D("0"),
    minimum_net_profit_factor=D("1"),
)


# Regression evidence.
#
# Используем агрегированные independently validated economics
# только для проверки decision semantics общего Gate.
#
# Следующим этапом adapter будет получать individual canonical trades.
CASES = (
    {
        "symbol": "NVTK@MISX",
        "trades": 1153,
        "gross_pnl": D("456.1"),
        "total_cost": D("1236.708750000"),
        "expected": (
            EconomicGateStatusV1
            .REJECT_NEGATIVE_EXPECTANCY
        ),
    },
    {
        "symbol": "PLZL@MISX",
        "trades": 1121,
        "gross_pnl": D("1034.0"),
        "total_cost": D("2057.080000000"),
        "expected": (
            EconomicGateStatusV1
            .REJECT_NEGATIVE_EXPECTANCY
        ),
    },
    {
        "symbol": "USDRUBF@RTSX",
        "trades": 2573,
        "gross_pnl": D("23195.000"),
        "total_cost": D("23528.5140730000"),
        "expected": (
            EconomicGateStatusV1
            .REJECT_NEGATIVE_EXPECTANCY
        ),
    },
)


def synthetic_trade_rows(
    *,
    trades: int,
    gross_pnl: Decimal,
    total_cost: Decimal,
) -> tuple[CanonicalEconomicTradeInputV1, ...]:
    """
    Только regression decision adapter.

    Равномерно распределяет уже подтвержденные агрегаты,
    чтобы проверить, что Economic Cost Gate воспроизводит
    знак net expectancy.

    Не используется как research/backtest implementation.
    """

    gross_per_trade = (
        gross_pnl / Decimal(trades)
    )

    cost_per_trade = (
        total_cost / Decimal(trades)
    )

    return tuple(
        CanonicalEconomicTradeInputV1(
            gross_pnl=gross_per_trade,
            commission=cost_per_trade,
            slippage=D("0"),
        )
        for _ in range(trades)
    )


def main() -> int:
    rejected = 0

    for case in CASES:
        rows = synthetic_trade_rows(
            trades=case["trades"],
            gross_pnl=case["gross_pnl"],
            total_cost=case["total_cost"],
        )

        result = evaluate_canonical_economic_gate_v1(
            rows,
            POLICY,
        )

        print(
            "ECONOMIC_GATE_REGRESSION_ROW "
            f"symbol={case['symbol']} "
            f"trades={result.trades} "
            f"gross_pnl={result.gross_pnl} "
            f"total_cost={result.total_cost} "
            f"net_pnl={result.net_pnl} "
            f"net_expectancy={result.net_expectancy} "
            f"status={result.status}"
        )

        if result.status != case["expected"]:
            raise RuntimeError(
                "ERROR=ECONOMIC_GATE_REGRESSION_MISMATCH "
                f"symbol={case['symbol']} "
                f"expected={case['expected']} "
                f"actual={result.status}"
            )

        rejected += int(
            result.status
            != EconomicGateStatusV1.PASS
        )

    print(
        f"regression_cases={len(CASES)}"
    )

    print(
        f"rejected_cases={rejected}"
    )

    print(
        "strategy_specific_logic_used=0"
    )

    print(
        "instrument_specific_logic_used=0"
    )

    print(
        "canonical_trade_replay_used=0"
    )

    print(
        "regression_mode=AGGREGATE_DECISION_SEMANTICS"
    )

    print("db_writes_performed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("economic_edge_claimed=0")
    print("micro_live_allowed=0")

    print(
        "VERDICT="
        "TREND_PULLBACK_ECONOMIC_GATE_REGRESSION_V1_OK"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
