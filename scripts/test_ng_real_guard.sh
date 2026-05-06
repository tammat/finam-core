#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export EXECUTION_MODE=real
export REAL_ORDER_CONFIRM=0
export FINAM_TOKEN=test.token.fake
export FINAM_ACCOUNT_ID=test-account

python - <<'PY'
from finam_core.adapters.grpc.orders_client import FinamOrdersClient
from finam_core.execution.real_execution import RealExecutionEngine

engine = RealExecutionEngine(FinamOrdersClient())

res = engine.execute({
    "symbol": "NGK6@RTSX",
    "side": "BUY",
    "qty": 1,
    "price": 2.80,
})

assert res.status == "REJECTED", res
assert res.reason == "REAL_ORDER_CONFIRM_not_enabled", res
print("NG_REAL_GUARD_OK")
PY
