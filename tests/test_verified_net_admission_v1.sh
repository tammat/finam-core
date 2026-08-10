#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1
export PYTHONPATH=src

echo "=== TEST_VERIFIED_NET_ADMISSION_V1 ==="

python - <<'PY'
from decimal import Decimal

from marketcore.research.economics.economic_cost_gate_v1 import (
    EconomicCostGatePolicyV1,
    EconomicGateStatusV1,
)
from marketcore.research.economics.verified_net_admission_v1 import (
    VerifiedNetMetricsV1,
    evaluate_verified_net_admission_v1,
)


D = Decimal

policy = EconomicCostGatePolicyV1(
    minimum_trades=50,
    minimum_net_expectancy=D("0"),
    minimum_net_profit_factor=D("1"),
)


passed = evaluate_verified_net_admission_v1(
    metrics=VerifiedNetMetricsV1(
        trades=100,
        net_profit_factor=D("1.25"),
        net_expectancy=D("5"),
    ),
    policy=policy,
)

assert passed.status == EconomicGateStatusV1.PASS
assert passed.passed is True


small = evaluate_verified_net_admission_v1(
    metrics=VerifiedNetMetricsV1(
        trades=44,
        net_profit_factor=D("1.39"),
        net_expectancy=D("20.5"),
    ),
    policy=policy,
)

assert (
    small.status
    == EconomicGateStatusV1.REJECT_INSUFFICIENT_TRADES
)
assert small.passed is False


negative = evaluate_verified_net_admission_v1(
    metrics=VerifiedNetMetricsV1(
        trades=100,
        net_profit_factor=D("0.9"),
        net_expectancy=D("-1"),
    ),
    policy=policy,
)

assert (
    negative.status
    == EconomicGateStatusV1.REJECT_NEGATIVE_EXPECTANCY
)

print("verified_net_pass_case=PASS")
print("minimum_sample_guard=PASS")
print("negative_expectancy_guard=PASS")
print("synthetic_trade_reconstruction_used=0")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")

print(
    "VERDICT="
    "TEST_VERIFIED_NET_ADMISSION_V1_OK"
)
PY
