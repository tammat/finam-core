#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/run_real_buy_execution_adapter.py \
  src/finam_core/execution/execution_intent_transition_service.py

grep -q "ExecutionIntentTransitionService" src/scripts/run_real_buy_execution_adapter.py
grep -q "transition_service.transition" src/scripts/run_real_buy_execution_adapter.py
grep -q 'next_state="SENDING"' src/scripts/run_real_buy_execution_adapter.py
grep -q 'next_state="SENT"' src/scripts/run_real_buy_execution_adapter.py
grep -q 'next_state="REJECTED"' src/scripts/run_real_buy_execution_adapter.py

echo "OK: real buy adapter wired to transition service"
