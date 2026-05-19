#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/execution/execution_lifecycle_determinism.py \
  src/scripts/run_execution_lifecycle_determinism.py

python - <<'PY'
from finam_core.execution.execution_lifecycle_determinism import (
    ExecutionLifecycleDeterminism,
)

v = ExecutionLifecycleDeterminism()

ok = v.validate_transition(
    previous_state="READY",
    next_state="RESERVED",
)

assert ok.allowed is True

bad = v.validate_transition(
    previous_state="READY",
    next_state="FILLED",
)

assert bad.allowed is False

closed = v.validate_transition(
    previous_state="FILLED",
    next_state="CLOSED",
)

assert closed.allowed is True

impossible = v.validate_transition(
    previous_state="CLOSED",
    next_state="ACK",
)

assert impossible.allowed is False

print("OK: execution lifecycle determinism")
PY
