#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/execution/execution_intent_router.py \
  src/scripts/run_execution_intent_router.py

python - <<'PY'
from finam_core.execution.execution_intent_router import (
    ExecutionIntentRouter,
)

r = ExecutionIntentRouter()

x = r.transition(
    current_state="READY",
    event="RESERVE",
)

assert x.next_state == "RESERVED"

y = r.transition(
    current_state="ACK",
    event="FILL",
)

assert y.next_state == "FILLED"

print("OK: execution intent router")
PY
