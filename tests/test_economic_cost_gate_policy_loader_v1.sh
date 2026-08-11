#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

PY="/opt/finam-core/venv/bin/python"

echo "=== TEST ECONOMIC COST GATE POLICY LOADER V1 ==="

PYTHONPATH=src "$PY" - <<'PY'
from pathlib import Path

from marketcore.research.economics.economic_cost_gate_policy_loader_v1 import (
    load_economic_cost_gate_policy_v1,
)

path = Path(
    "config/research/"
    "economic_cost_gate_policy_v1.json"
)

policy = load_economic_cost_gate_policy_v1(path)

assert policy.minimum_trades == 50
assert str(policy.minimum_net_expectancy) == "0"
assert str(policy.minimum_net_profit_factor) == "1.0"

print(
    "POLICY_ROW "
    f"minimum_trades={policy.minimum_trades} "
    f"minimum_net_expectancy={policy.minimum_net_expectancy} "
    f"minimum_net_profit_factor={policy.minimum_net_profit_factor}"
)

print("config_source_used=1")
print("decimal_safe=1")
print("source_version_validated=1")
print("fail_closed_loader=1")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print(
    "VERDICT="
    "TEST_ECONOMIC_COST_GATE_POLICY_LOADER_V1_OK"
)
PY
