#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
source /opt/finam-core/deploy/env/.env

python -m py_compile \
  src/finam_core/execution/position_lifecycle_state_repository.py

python - <<'PY'
from finam_core.execution.position_lifecycle_state_repository import (
    PositionLifecycleStateRepository,
)

r = PositionLifecycleStateRepository()

row_id = r.upsert_state(
    symbol="TEST@MISX",
    strategy="default",
    entry_price=100,
    initial_qty=5,
    remaining_qty=3,
    tp1_done=True,
    tp2_done=False,
    profit_lock_done=True,
    trailing_active=True,
    current_stop=104,
    current_take_profit=110,
    raw={"test": True},
)

assert row_id is not None

state = r.load_state(
    symbol="TEST@MISX",
    strategy="default",
)

assert state is not None
assert state["tp1_done"] is True
assert state["remaining_qty"] == 3
assert state["current_stop"] == 104

print("OK: position lifecycle state repository")
PY
