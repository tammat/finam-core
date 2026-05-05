#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export EXECUTION_MODE=real
unset REAL_ORDER_CONFIRM

python - <<'PY'
from finam_core.adapters.grpc.orders_client import FinamOrdersClient
from finam_core.execution.real_execution import RealExecutionEngine

client = FinamOrdersClient()
engine = RealExecutionEngine(client)

res = engine.execute({
    "symbol": "BRM6@RTSX",
    "side": "BUY",
    "qty": 1,
    "price": 110.5,
})

assert res.status == "REJECTED", res
assert res.reason in (
    "FINAM_ACCOUNT_ID_not_set",
    "FINAM_TOKEN_not_set",
    "REAL_ORDER_CONFIRM_not_enabled",
), res

print("FINAM_ORDERS_CLIENT_SAFE_OK")
PY
