#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python - <<'PY'
from finam_core.portfolio.position_state_reconciliation import (
    PositionStateInput,
    reconcile_position_state,
)

ok = reconcile_position_state(
    PositionStateInput(
        symbol="SBER@MISX",
        broker_qty=10,
        local_qty=10,
        lifecycle_qty=10,
        managed_qty=10,
    )
)
assert ok.status == "OK"

bad = reconcile_position_state(
    PositionStateInput(
        symbol="BRM6@RTSX",
        broker_qty=5,
        local_qty=0,
        lifecycle_qty=0,
        managed_qty=0,
    )
)
assert bad.status == "BROKER_LOCAL_MISMATCH"
assert bad.severity == "CRITICAL"

print("TEST_POSITION_STATE_RECONCILIATION_OK")
PY

python -m py_compile \
  src/finam_core/portfolio/position_state_reconciliation.py \
  src/finam_core/portfolio/position_state_reconciliation_repository.py \
  src/scripts/build_position_state_reconciliation.py
