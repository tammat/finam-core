from __future__ import annotations

from decimal import Decimal

from marketcore.research.net_first_edge_pipeline_v1 import (
    NetFirstPipelineStatusV1,
    evaluate_net_first_candidate_v1,
)
from marketcore.research.economics.canonical_economic_gate_adapter_v1 import (
    CanonicalEconomicTradeInputV1,
)
from marketcore.research.economics.economic_cost_gate_v1 import (
    EconomicCostGatePolicyV1,
)


D = Decimal

POLICY = EconomicCostGatePolicyV1(
    minimum_trades=50,
    minimum_net_expectancy=D("0"),
    minimum_net_profit_factor=D("1"),
)

CASES = (
    {
        "symbol": "NVTK@MISX",
        "trades": 1153,
        "gross_pnl": D("456.1"),
        "total_cost": D("1236.708750000"),
    },
    {
        "symbol": "PLZL@MISX",
        "trades": 1121,
        "gross_pnl": D("1034.0"),
        "total_cost": D("2057.080000000"),
    },
    {
        "symbol": "USDRUBF@RTSX",
        "trades": 2573,
        "gross_pnl": D("23195.0"),
        "total_cost": D("23528.514073"),
    },
)


def build_rows(case):
    gross_per_trade = (
        case["gross_pnl"]
        / D(case["trades"])
    )

    cost_per_trade = (
        case["total_cost"]
        / D(case["trades"])
    )

    return tuple(
        CanonicalEconomicTradeInputV1(
            gross_pnl=gross_per_trade,
            commission=cost_per_trade,
            slippage=D("0"),
        )
        for _ in range(case["trades"])
    )


def main() -> int:
    robustness_calls = 0
    rejected = 0

    def robustness_probe():
        nonlocal robustness_calls
        robustness_calls += 1

    for case in CASES:
        result = evaluate_net_first_candidate_v1(
            economic_trades=build_rows(case),
            economic_policy=POLICY,
            robustness_runner=robustness_probe,
        )

        print(
            "NET_FIRST_CONTROL_ROW "
            f"symbol={case['symbol']} "
            f"status={result.status} "
            f"economic_status="
            f"{result.economic_result.status} "
            f"net_pnl={result.economic_result.net_pnl} "
            f"net_expectancy="
            f"{result.economic_result.net_expectancy} "
            f"net_profit_factor="
            f"{result.economic_result.net_profit_factor} "
            f"robustness_called="
            f"{int(result.robustness_called)}"
        )

        if (
            result.status
            != NetFirstPipelineStatusV1.REJECT_ECONOMIC_GATE
        ):
            raise RuntimeError(
                "ERROR=CONTROL_CASE_NOT_REJECTED "
                f"symbol={case['symbol']}"
            )

        rejected += 1

    if robustness_calls != 0:
        raise RuntimeError(
            "ERROR=ROBUSTNESS_CALLED_FOR_REJECTED_CANDIDATE "
            f"calls={robustness_calls}"
        )

    print(f"candidates={len(CASES)}")
    print(f"economic_gate_reject={rejected}")
    print("economic_gate_pass=0")
    print(f"robustness_scheduled={robustness_calls}")
    print(f"robustness_saved={rejected}")

    print("economic_gate_before_robustness=1")
    print("production_robustness_runner_used=0")
    print("control_mode=ADMISSION_INTEGRATION")
    print("db_writes_performed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("economic_edge_claimed=0")
    print("micro_live_allowed=0")

    print(
        "VERDICT="
        "NET_FIRST_TREND_PULLBACK_CONTROL_INTEGRATION_V1_OK"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
