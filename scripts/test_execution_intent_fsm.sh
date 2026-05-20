#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/execution/execution_intent_fsm.py

python - <<'PY'
from finam_core.execution.execution_intent_fsm import ExecutionIntentFSM

fsm = ExecutionIntentFSM()

assert fsm.validate(previous_state="READY", next_state="RESERVED").allowed is True
assert fsm.validate(previous_state="RESERVED", next_state="SENDING").allowed is True
assert fsm.validate(previous_state="SENDING", next_state="FILLED").allowed is True
assert fsm.validate(previous_state="SENT", next_state="ACK").allowed is True
assert fsm.validate(previous_state="ACK", next_state="CANCELLED").allowed is True
assert fsm.validate(previous_state="RECONCILE_REQUIRED", next_state="FILLED").allowed is True

assert fsm.validate(previous_state="READY", next_state="FILLED").allowed is False
assert fsm.validate(previous_state="CANCELLED", next_state="FILLED").allowed is False
assert fsm.validate(previous_state="REJECTED", next_state="ACK").allowed is False

print("OK: execution intent FSM")
PY
