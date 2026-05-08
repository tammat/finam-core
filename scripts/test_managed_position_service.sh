#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.execution.position_registry import ManagedPosition
from finam_core.execution.managed_position_service import ManagedPositionService

svc = ManagedPositionService()

svc.remove("BRM6")

p = ManagedPosition(
    symbol="BRM6",
    side="SHORT",
    qty=2,
    entry_price=98.32,
    stop_order_id="stop-1",
)

svc.register(p)

loaded = svc.get("BRM6")

assert loaded is not None
assert loaded.symbol == "BRM6"

tp1 = svc.mark_tp1_filled("BRM6")
assert tp1.tp1_done is True

be = svc.mark_breakeven_done(
    "BRM6",
    stop_order_id="stop-be",
)

assert be.breakeven_done is True
assert be.stop_order_id == "stop-be"

svc.remove("BRM6")

assert svc.get("BRM6") is None

print("MANAGED_POSITION_SERVICE_OK")
PY
