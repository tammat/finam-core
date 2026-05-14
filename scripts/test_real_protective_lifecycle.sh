#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/execution/real_protective_lifecycle.py

python - <<'PY'
from finam_core.execution.real_protective_lifecycle import RealProtectiveLifecycleEngine

class FakeOrders:
    def place_stop_order(self, **kwargs):
        return {"status": "ACCEPTED", "order_id": "stop-1", "reason": "ok"}

engine = RealProtectiveLifecycleEngine(FakeOrders())

# По умолчанию реальные заявки запрещены.
r = engine.place_or_replace_stop(
    symbol="BRM6@RTSX",
    side="SELL",
    qty=1,
    stop_price=106.0,
)

assert r.executed is False
assert r.status == "DRY_RUN_OR_DISABLED"

print("OK: real protective lifecycle safe by default")
PY
