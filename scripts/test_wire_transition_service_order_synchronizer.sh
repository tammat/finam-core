#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/run_real_order_state_synchronizer.py \
  src/finam_core/execution/execution_intent_transition_service.py

grep -q "ExecutionIntentTransitionService" src/scripts/run_real_order_state_synchronizer.py
grep -q "transition_service.transition" src/scripts/run_real_order_state_synchronizer.py
grep -q "REAL_ORDER_STATE_SYNC_TRANSITION_BLOCKED" src/scripts/run_real_order_state_synchronizer.py

echo "OK: order synchronizer wired to transition service"
