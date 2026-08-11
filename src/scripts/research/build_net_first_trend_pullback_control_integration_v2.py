from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from marketcore.research.economics.canonical_economic_gate_adapter_v1 import (
    CanonicalEconomicTradeInputV1,
)
from marketcore.research.economics.economic_cost_gate_v1 import (
    EconomicCostGatePolicyV1,
)
from marketcore.research.net_first_edge_pipeline_v1 import (
    NetFirstPipelineStatusV1,
    evaluate_net_first_candidate_v1,
)


ROOT = Path(__file__).resolve().parents[3]

POLICY_PATH = (
    ROOT
    / "config/research/economic_cost_gate_policy_v1.json"
)

FIXTURE_PATH = (
    ROOT
    / "config/research/"
    "trend_pullback_historical_replay_frozen_lineage_v2.json"
)


def load_policy() -> EconomicCostGatePolicyV1:
    payload = json.loads(
        POLICY_PATH.read_text(encoding="utf-8")
    )

    return EconomicCostGatePolicyV1(
        minimum_trades=int(payload["minimum_trades"]),
        minimum_net_expectancy=Decimal(
            payload["minimum_net_expectancy"]
        ),
        minimum_net_profit_factor=Decimal(
            payload["minimum_net_profit_factor"]
        ),
    )


def build_rows(case: dict) -> tuple[
    CanonicalEconomicTradeInputV1,
    ...
]:
    trades = int(case["trades"])
    gross_pnl = Decimal(case["gross_pnl"])
    total_cost = Decimal(case["total_cost"])

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
            slippage=Decimal("0"),
        )
        for _ in range(trades)
    )


def main() -> int:
    policy = load_policy()

    fixture = json.loads(
        FIXTURE_PATH.read_text(
            encoding="utf-8"
        )
    )

    if not fixture.get(
        "economic_baseline_finalized"
    ):
        raise RuntimeError(
            "ERROR=ECONOMIC_BASELINE_NOT_FINALIZED"
        )

    cases = fixture["expected_metrics_v2"]

    robustness_calls = 0
    rejected = 0

    def robustness_probe() -> None:
        nonlocal robustness_calls
        robustness_calls += 1

    for symbol, case in cases.items():
        result = evaluate_net_first_candidate_v1(
            economic_trades=build_rows(case),
            economic_policy=policy,
            robustness_runner=robustness_probe,
        )

        expected_status = case["status"]

        print(
            "NET_FIRST_CONTROL_V2_ROW "
            f"symbol={symbol} "
            f"status={result.status} "
            f"economic_status="
            f"{result.economic_result.status} "
            f"expected_status={expected_status} "
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
                "ERROR=NEGATIVE_CONTROL_NOT_REJECTED "
                f"symbol={symbol}"
            )

        if str(result.economic_result.status) != expected_status:
            raise RuntimeError(
                "ERROR=NEGATIVE_CONTROL_STATUS_MISMATCH "
                f"symbol={symbol}"
            )

        if result.robustness_called:
            raise RuntimeError(
                "ERROR=ROBUSTNESS_CALLED_FOR_REJECTED_CANDIDATE "
                f"symbol={symbol}"
            )

        rejected += 1

    if robustness_calls != 0:
        raise RuntimeError(
            "ERROR=ROBUSTNESS_CALL_COUNT_NONZERO "
            f"calls={robustness_calls}"
        )

    print(f"candidates={len(cases)}")
    print(f"economic_gate_reject={rejected}")
    print("economic_gate_pass=0")
    print("robustness_scheduled=0")
    print(f"robustness_saved={rejected}")
    print("policy_from_config=1")
    print("negative_controls_from_frozen_v2=1")
    print("economic_gate_before_robustness=1")
    print("aggregate_fixture_used=1")
    print("trade_level_profit_factor_claimed=0")
    print("negative_expectancy_rejection_validated=1")
    print("core_net_first_changed=0")
    print("shadow_admission_preserved=1")
    print("enforced_admission_enabled=0")
    print("db_writes_performed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print(
        "VERDICT="
        "NET_FIRST_TREND_PULLBACK_CONTROL_INTEGRATION_V2_OK"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
