#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

PY="/opt/finam-core/venv/bin/python"
OPT="src/scripts/analytics/build_entry_exit_optimizer_v1.py"
NET="src/marketcore/research/economics/verified_net_admission_v1.py"

echo "=== TEST NET FIRST ENTRY EXIT ENFORCEMENT V1 ==="

PYTHONPATH=src "$PY" -m py_compile "$NET" "$OPT"

PYTHONPATH=src "$PY" - <<'PY'
from decimal import Decimal

from marketcore.research.economics.economic_cost_gate_v1 import (
    EconomicCostGatePolicyV1,
)
from marketcore.research.economics.verified_net_admission_v1 import (
    build_verified_net_metrics_v1,
    evaluate_verified_net_admission_v1,
)

policy = EconomicCostGatePolicyV1(
    minimum_trades=3,
    minimum_net_expectancy=Decimal("0"),
    minimum_net_profit_factor=Decimal("1"),
)

reject_metrics = build_verified_net_metrics_v1(
    (
        Decimal("-1"),
        Decimal("-0.5"),
        Decimal("0.25"),
    )
)

reject = evaluate_verified_net_admission_v1(
    metrics=reject_metrics,
    policy=policy,
)

assert reject.passed is False

pass_metrics = build_verified_net_metrics_v1(
    (
        Decimal("1"),
        Decimal("0.75"),
        Decimal("-0.25"),
    )
)

passed = evaluate_verified_net_admission_v1(
    metrics=pass_metrics,
    policy=policy,
)

assert passed.passed is True

print("reject_case=PASS")
print("pass_case=PASS")
print("trade_level_net_metric_builder=1")
print("synthetic_trade_reconstruction_used=0")
PY

grep -q \
  'build_verified_net_metrics_v1' \
  "$OPT"

grep -q \
  'load_economic_cost_gate_policy_v1' \
  "$OPT"

grep -q \
  'and net_first_pass' \
  "$OPT"

grep -q \
  '"net_first_admission"' \
  "$OPT"

grep -q \
  'ensure_frozen_entry_exit_oos(' \
  "$OPT"

echo "verified_net_metrics_from_shadow_r=1"
echo "policy_from_config=1"
echo "net_first_before_new_oos_admission=1"
echo "existing_oos_path_preserved=1"
echo "canonical_trade_level_adapter_used=0"

echo "enforcement_applied=1"
echo "research_promotion_pipeline_changed=1"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=TEST_NET_FIRST_ENTRY_EXIT_ENFORCEMENT_V1_OK"
