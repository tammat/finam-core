#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.execution.position_registry import PositionRegistry, ManagedPosition

r = PositionRegistry()

p = r.register_position(
    ManagedPosition(
        symbol="BRM6",
        side="SHORT",
        qty=2,
        entry_price=98.32,
        stop_order_id="stop-1",
        tp1_order_id="tp1-1",
        tp2_order_id="tp2-1",
    )
)

assert r.get("BRM6") == p
assert r.get("BRM6").tp1_done is False

p1 = r.mark_tp1_filled("BRM6")
assert p1.tp1_done is True

p1_again = r.mark_tp1_filled("BRM6")
assert p1_again.tp1_done is True

p2 = r.mark_breakeven_done("BRM6", stop_order_id="stop-be")
assert p2.breakeven_done is True
assert p2.stop_order_id == "stop-be"

p3 = r.update_stop("BRM6", "stop-new")
assert p3.stop_order_id == "stop-new"

removed = r.remove("BRM6")
assert removed.symbol == "BRM6"
assert r.get("BRM6") is None

print("POSITION_REGISTRY_OK")
PY
