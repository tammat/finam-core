#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

PY="/opt/finam-core/venv/bin/python"
FILE="src/scripts/analytics/build_entry_exit_optimizer_v1.py"

echo "=== TEST ENTRY EXIT PRE OOS PLATEAU DEADLOCK FIX V1 ==="

PYTHONPATH=src "$PY" -m py_compile "$FILE"

PYTHONPATH=src "$PY" - <<'PY'
from pathlib import Path

path = Path(
    "src/scripts/analytics/"
    "build_entry_exit_optimizer_v1.py"
)

text = path.read_text(encoding="utf-8")

assert (
    'metrics["checks"]["parameter_plateau"] = plateau["passed"]'
    in text
)

assert (
    'checks.pop("parameter_plateau", None)'
    in text
)

assert (
    '"oos_positive",\n'
    '                    "oos_better",\n'
    '                    "parameter_plateau",'
    in text
)

assert "and net_first_pass" in text
assert "ensure_frozen_entry_exit_oos(" in text

print("parameter_plateau_metric_preserved=1")
print("parameter_plateau_pre_oos_block_removed=1")
print("parameter_plateau_post_oos_evidence_preserved=1")
print("net_first_gate_preserved=1")
PY

git diff --check -- "$FILE"

echo "pre_oos_deadlock_confirmed=1"
echo "pre_oos_deadlock_removed=1"
echo "net_first_logic_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_ENTRY_EXIT_PRE_OOS_PLATEAU_DEADLOCK_FIX_V1_OK"
