#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.portfolio.real_position_to_managed_sync import RealPositionToManagedSync
from finam_core.execution.managed_position_service import ManagedPositionService

svc = ManagedPositionService()
sync = RealPositionToManagedSync(managed=svc)

count = sync.sync()

assert count >= 1

br = svc.get("BRM6")
ng = svc.get("NGK6")

assert br is not None
assert ng is not None

assert br.side == "SHORT"
assert br.qty == 2
assert br.entry_price == 98.32

assert ng.side == "LONG"
assert ng.qty == 3
assert ng.entry_price == 2.841

print("REAL_POSITION_TO_MANAGED_SYNC_OK", "count=", count)
PY
