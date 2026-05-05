#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export EXECUTION_MODE=real_dry_run

python - <<'PY'
from finam_core.execution.real_execution import RealExecutionEngine

class FakeOrdersClient:
    def place_market_order(self, **kwargs):
        raise AssertionError("real order must not be sent in dry_run")

engine = RealExecutionEngine(FakeOrdersClient())

res = engine.execute({
    "symbol": "BRM6@RTSX",
    "side": "BUY",
    "qty": 1,
    "price": 110.5,
})

assert res.status == "DRY_RUN_ACCEPTED"
assert res.order_id.startswith("dry_")

print("REAL_EXECUTION_DRY_RUN_OK")
PY
