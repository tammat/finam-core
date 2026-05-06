#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export REAL_EXECUTION_ENABLED=0
export REAL_ORDER_CONFIRM=0

python - <<'PY'
from finam_core.adapters.grpc.orders_client import FinamOrdersClient

c = FinamOrdersClient()

r = c.cancel_order("test_order_1")
assert r["status"] == "DRY_RUN_CANCEL", r

r = c.place_stop_order(
    symbol="BRM6@RTSX",
    side="SELL",
    qty=1,
    stop_price=100.0,
)
assert r["status"] == "DRY_RUN_ACCEPTED", r
assert r["order_id"].startswith("dry_stop_"), r

bad = c.place_stop_order(
    symbol="BRM6@RTSX",
    side="SELL",
    qty=0,
    stop_price=100.0,
)
assert bad["status"] == "REJECTED", bad

print("FINAM_ORDERS_CANCEL_REPLACE_METHODS_OK")
PY
