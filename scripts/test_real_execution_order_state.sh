#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export REAL_EXECUTION_ENABLED=1
export REAL_ORDER_CONFIRM=1
export EXECUTION_MODE=real

python - <<'PY'
from finam_core.execution.real_execution import RealExecutionEngine


class DummyOrdersClient:
    def place_market_order(self, symbol, side, qty, price=None):
        return {
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "price": price,
            "status": "ACCEPTED",
            "order_id": "broker_1",
        }


engine = RealExecutionEngine(orders_client=DummyOrdersClient())
engine.mode = "real"

r = engine.execute(symbol="BRM6@RTSX", side="BUY", qty=3, price=100.0)

assert r.status == "ACCEPTED", r
assert r.order_id == "broker_1", r
assert "broker_1" in engine.orders_by_id, engine.orders_by_id

state = engine.orders_by_id["broker_1"]
assert state.state == "ACCEPTED", state
assert state.symbol == "BRM6@RTSX", state
assert state.qty == 3.0, state

print("REAL_EXECUTION_ORDER_STATE_OK")
PY
