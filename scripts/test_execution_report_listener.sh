#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export REAL_EXECUTION_ENABLED=1
export REAL_ORDER_CONFIRM=1
export EXECUTION_MODE=real
export ENABLE_ORDER_EVENT_STORE=0

python - <<'PY'
from finam_core.execution.real_execution import RealExecutionEngine
from finam_core.execution.execution_report_listener import ExecutionReportListener


class DummyOrdersClient:
    def place_market_order(self, symbol, side, qty, price=None):
        return {
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "price": price,
            "status": "ACCEPTED",
            "order_id": "broker_fill_1",
        }


engine = RealExecutionEngine(orders_client=DummyOrdersClient())
engine.mode = "real"

r = engine.execute(symbol="BRM6@RTSX", side="BUY", qty=3, price=100.0)
assert r.status == "ACCEPTED", r

listener = ExecutionReportListener(engine)

r = listener.on_report({
    "order_id": "broker_fill_1",
    "symbol": "BRM6@RTSX",
    "side": "BUY",
    "status": "PARTIAL_FILLED",
    "fill_qty": 1,
    "fill_price": 100.5,
})

assert r.status == "PARTIAL_FILLED", r
assert r.raw["filled_qty"] == 1.0, r
assert r.raw["remaining_qty"] == 2.0, r

r = listener.on_report({
    "order_id": "broker_fill_1",
    "symbol": "BRM6@RTSX",
    "side": "BUY",
    "status": "FILLED",
    "fill_qty": 2,
    "fill_price": 101.0,
})

assert r.status == "FILLED", r
assert r.raw["filled_qty"] == 3.0, r
assert r.raw["remaining_qty"] == 0.0, r

ignored = listener.on_report({
    "order_id": "broker_fill_1",
    "status": "ACCEPTED",
})
assert ignored["status"] == "IGNORED", ignored

print("EXECUTION_REPORT_LISTENER_OK")
PY
