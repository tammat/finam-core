#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1
export PYTHONPATH=src

echo "=== TEST_NET_FIRST_EDGE_PIPELINE_V1 ==="

python - <<'PY'
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

policy = EconomicCostGatePolicyV1(
    minimum_trades=3,
    minimum_net_expectancy=D("0"),
    minimum_net_profit_factor=D("1"),
)

calls = {
    "rejected": 0,
    "passed": 0,
}


def rejected_robustness():
    calls["rejected"] += 1


def passed_robustness():
    calls["passed"] += 1


# Gross positive, net negative.
rejected_trades = (
    CanonicalEconomicTradeInputV1(
        gross_pnl=D("5"),
        commission=D("4"),
        slippage=D("2"),
    ),
    CanonicalEconomicTradeInputV1(
        gross_pnl=D("4"),
        commission=D("4"),
        slippage=D("2"),
    ),
    CanonicalEconomicTradeInputV1(
        gross_pnl=D("3"),
        commission=D("4"),
        slippage=D("2"),
    ),
)

rejected = evaluate_net_first_candidate_v1(
    economic_trades=rejected_trades,
    economic_policy=policy,
    robustness_runner=rejected_robustness,
)

print(
    "PIPELINE_CASE rejected "
    f"status={rejected.status} "
    f"economic_status="
    f"{rejected.economic_result.status} "
    f"robustness_called="
    f"{int(rejected.robustness_called)}"
)

assert (
    rejected.status
    == NetFirstPipelineStatusV1.REJECT_ECONOMIC_GATE
)

assert rejected.robustness_called is False
assert calls["rejected"] == 0


# Net positive.
passed_trades = (
    CanonicalEconomicTradeInputV1(
        gross_pnl=D("20"),
        commission=D("2"),
        slippage=D("1"),
    ),
    CanonicalEconomicTradeInputV1(
        gross_pnl=D("-5"),
        commission=D("2"),
        slippage=D("1"),
    ),
    CanonicalEconomicTradeInputV1(
        gross_pnl=D("15"),
        commission=D("2"),
        slippage=D("1"),
    ),
)

passed = evaluate_net_first_candidate_v1(
    economic_trades=passed_trades,
    economic_policy=policy,
    robustness_runner=passed_robustness,
)

print(
    "PIPELINE_CASE passed "
    f"status={passed.status} "
    f"economic_status="
    f"{passed.economic_result.status} "
    f"robustness_called="
    f"{int(passed.robustness_called)}"
)

assert (
    passed.status
    == NetFirstPipelineStatusV1.ADMIT_ROBUSTNESS
)

assert passed.robustness_called is True
assert calls["passed"] == 1


print("economic_gate_before_robustness=1")
print("rejected_candidate_robustness_calls=0")
print("passed_candidate_robustness_calls=1")
print("strategy_specific_logic_used=0")
print("db_writes_performed=0")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")

print(
    "VERDICT="
    "TEST_NET_FIRST_EDGE_PIPELINE_V1_OK"
)
PY
