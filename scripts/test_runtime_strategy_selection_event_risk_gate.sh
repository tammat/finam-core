#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile src/scripts/build_runtime_strategy_selection.py

grep -q "strategy_event_risk_context" src/scripts/build_runtime_strategy_selection.py
grep -q "EVENT_BLOCKED" src/scripts/build_runtime_strategy_selection.py
grep -q "event_risk_block" src/scripts/build_runtime_strategy_selection.py

echo "TEST_RUNTIME_STRATEGY_SELECTION_EVENT_RISK_GATE_OK"
