#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export REAL_EXECUTION_ENABLED=1
export REAL_ORDER_CONFIRM=0

python - <<'PY'
from finam_core.adapters.grpc.orders_client import FinamOrdersClient

client = FinamOrdersClient()

r = client.place_limit_order(
    symbol="SVETP@MISX",
    side="BUY",
    qty=10,
    limit_price=26.50,
)

assert r["status"] == "DRY_RUN_ACCEPTED", r
assert r["symbol"] == "SVETP@MISX", r
assert r["side"] == "BUY", r
assert float(r["qty"]) == 10.0, r
assert float(r["limit_price"]) == 26.50, r
assert str(r["order_id"]).startswith("dry_limit_"), r

print("PLACE_LIMIT_ORDER_DRY_RUN_OK")
PY
