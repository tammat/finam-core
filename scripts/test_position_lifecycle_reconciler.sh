#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/execution/position_lifecycle_reconciler.py \
  src/finam_core/execution/position_lifecycle_state_repository.py

python - <<'PY'
from finam_core.execution.position_lifecycle_reconciler import PositionLifecycleReconciler

r = PositionLifecycleReconciler()

d = r.reconcile(symbol="BRM6@RTSX", expected_remaining_qty=1, actual_qty=0)
assert d.action == "CLEAR_STATE"

d = r.reconcile(symbol="BRM6@RTSX", expected_remaining_qty=1, actual_qty=0.5)
assert d.action == "UPDATE_REMAINING_QTY"

d = r.reconcile(symbol="BRM6@RTSX", expected_remaining_qty=1, actual_qty=1)
assert d.action == "OK"

print("OK: position lifecycle reconciler")
PY
