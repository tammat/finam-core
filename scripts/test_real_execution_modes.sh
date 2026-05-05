#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

EXECUTION_MODE=real_dry_run python - <<'PY'
from finam_core.execution.real_execution import RealExecutionEngine

engine = RealExecutionEngine(None)
res = engine.execute({"symbol": "BRM6@RTSX", "side": "BUY", "qty": 1, "price": 110.5})
assert res.status == "DRY_RUN_ACCEPTED", res
print("REAL_DRY_RUN_MODE_OK")
PY

EXECUTION_MODE=real python - <<'PY'
from finam_core.execution.real_execution import RealExecutionEngine

engine = RealExecutionEngine(None)
res = engine.execute({"symbol": "BRM6@RTSX", "side": "BUY", "qty": 1, "price": 110.5})
assert res.status == "REJECTED", res
assert res.reason == "orders_client_not_configured", res
print("REAL_MODE_SAFE_REJECT_OK")
PY
