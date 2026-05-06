#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.execution.open_orders_sync import OpenOrdersSync

sync = OpenOrdersSync()

orders = [
    {"order_id": "s1", "symbol": "BRM6@RTSX", "side": "SELL", "status": "ACTIVE", "type": "STOP", "stop": 102.8, "qty": 1},
    {"order_id": "t1", "symbol": "BRM6@RTSX", "side": "SELL", "status": "WORKING", "type": "TAKE_PROFIT", "price": 105.0, "qty": 1},
    {"order_id": "x1", "symbol": "BRM6@RTSX", "side": "SELL", "status": "CANCELLED", "type": "STOP", "qty": 1},
    {"order_id": "n1", "symbol": "NGK6@RTSX", "side": "BUY", "status": "ACTIVE", "type": "LIMIT", "price": 2.7, "qty": 3},
]

by_symbol = sync.build_orders_by_symbol(orders)

assert "BRM6@RTSX" in by_symbol, by_symbol
assert len(by_symbol["BRM6@RTSX"]) == 2, by_symbol
assert by_symbol["BRM6@RTSX"][0]["stop_price"] == 102.8, by_symbol
assert "NGK6@RTSX" in by_symbol, by_symbol

print("OPEN_ORDERS_SYNC_OK")
PY
