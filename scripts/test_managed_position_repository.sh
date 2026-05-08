#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.execution.position_registry import ManagedPosition
from finam_core.storage.managed_position_repository import ManagedPositionRepository

repo = ManagedPositionRepository()

repo.ensure_schema()

repo.delete("BRM6")

p = ManagedPosition(
    symbol="BRM6",
    side="SHORT",
    qty=2,
    entry_price=98.32,
    stop_order_id="stop-1",
    tp1_order_id="tp1-1",
    tp2_order_id="tp2-1",
)

repo.save(p)

loaded = repo.get("BRM6")

assert loaded is not None
assert loaded.symbol == "BRM6"
assert loaded.qty == 2
assert loaded.stop_order_id == "stop-1"

all_positions = repo.list_all()

assert any(x.symbol == "BRM6" for x in all_positions)

repo.delete("BRM6")

assert repo.get("BRM6") is None

print("MANAGED_POSITION_REPOSITORY_OK")
PY
