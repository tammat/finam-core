#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.execution.cancel_replace_stop_manager import CancelReplaceStopManager


class DummyOrdersClient:
    def __init__(self):
        self.cancelled = []
        self.placed = []

    def cancel_order(self, order_id):
        self.cancelled.append(order_id)
        return {"status": "CANCELED", "order_id": order_id}

    def place_stop_order(self, symbol, side, qty, stop_price):
        self.placed.append((symbol, side, qty, stop_price))
        return {
            "status": "ACCEPTED",
            "order_id": "new_stop_1",
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "stop_price": stop_price,
        }


client = DummyOrdersClient()
mgr = CancelReplaceStopManager(client)

r = mgr.replace_stop(
    symbol="BRM6@RTSX",
    old_order_id="old_stop_1",
    side="SELL",
    qty=1,
    stop_price=101.5,
)

assert r.status == "ACCEPTED", r
assert r.old_order_id == "old_stop_1", r
assert r.new_order_id == "new_stop_1", r
assert client.cancelled == ["old_stop_1"], client.cancelled
assert client.placed == [("BRM6@RTSX", "SELL", 1, 101.5)], client.placed

bad = mgr.replace_stop(
    symbol="BRM6@RTSX",
    old_order_id="",
    side="SELL",
    qty=1,
    stop_price=101.5,
)
assert bad.status == "REJECTED", bad

print("CANCEL_REPLACE_STOP_MANAGER_OK")
PY
