#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export REAL_EXECUTION_ENABLED=0
export REAL_ORDER_CONFIRM=0

python - <<'PY'
import os
from finam_core.adapters.grpc.orders_client import FinamOrdersClient

client = FinamOrdersClient.__new__(FinamOrdersClient)

def fake_validate(symbol, side, qty):
    return None

client._validate = fake_validate

resp = client.place_limit_order(
    symbol="SBER@MISX",
    side="BUY",
    qty=1,
    limit_price=300.0,
)

assert resp["status"] == "DRY_RUN_ACCEPTED", resp
assert resp["symbol"] == "SBER@MISX"
assert resp["side"] == "BUY"
assert resp["qty"] == 1.0
assert resp["limit_price"] == 300.0
assert resp["reason"] == "real_order_confirm_disabled"

print("OK: place_limit_order dry-run protected")
PY
