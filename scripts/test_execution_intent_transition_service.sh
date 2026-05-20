#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/execution/execution_intent_transition_service.py \
  src/finam_core/execution/execution_intent_fsm.py \
  src/finam_core/execution/execution_state_transition_logger.py

python - <<'PY'
from finam_core.execution.execution_intent_transition_service import (
    ExecutionIntentTransitionResult,
    ExecutionIntentTransitionService,
)

svc = ExecutionIntentTransitionService()

assert svc.fsm.validate(previous_state="READY", next_state="RESERVED").allowed is True
assert svc.fsm.validate(previous_state="READY", next_state="FILLED").allowed is False

r = ExecutionIntentTransitionResult(
    applied=True,
    intent_id=1,
    previous_state="READY",
    next_state="RESERVED",
    reason="test",
)

assert r.applied is True
assert r.intent_id == 1

print("OK: execution intent transition service")
PY
