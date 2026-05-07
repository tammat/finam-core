#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export EXECUTION_MODE=real_dry_run
export REAL_EXECUTION_ENABLED=1
export REAL_ORDER_CONFIRM=1

python - <<'PY'
from finam_core.execution.execution_dispatcher import ExecutionDispatcher
from finam_core.execution.real_execution import RealExecutionEngine


class DummyOrdersClient:
    def place_stop_order(self, symbol, side, qty, stop_price):
        return {
            "status": "DRY_RUN_ACCEPTED",
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "stop_price": stop_price,
            "order_id": f"stop_{symbol}_{side}_{qty}_{stop_price}",
        }

    def place_limit_order(self, symbol, side, qty, limit_price):
        return {
            "status": "DRY_RUN_ACCEPTED",
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "limit_price": limit_price,
            "order_id": f"limit_{symbol}_{side}_{qty}_{limit_price}",
        }

    def place_market_order(self, *args, **kwargs):
        raise RuntimeError("REAL MARKET ORDER MUST NOT BE CALLED BY DummyOrdersClient")


orders = DummyOrdersClient()
real = RealExecutionEngine(orders_client=orders)
dispatcher = ExecutionDispatcher(orders_client=orders, real_execution_engine=real)

stop = dispatcher.dispatch(
    {
        "symbol": "BRM6@RTSX",
        "side": "BUY",
        "qty": 1,
        "order_route": "STOP_ORDER",
        "stop_price": 103.2,
    },
    {"last": 102.8},
)
assert stop.status == "DRY_RUN_ACCEPTED", stop
assert stop.route == "STOP_ORDER", stop
assert stop.order_id == "stop_BRM6@RTSX_BUY_1.0_103.2", stop

limit = dispatcher.dispatch(
    {
        "symbol": "BRM6@RTSX",
        "side": "BUY",
        "qty": 1,
        "order_route": "LIMIT_ORDER",
        "limit_price": 102.1,
    },
    {"last": 102.8},
)
assert limit.status == "DRY_RUN_ACCEPTED", limit
assert limit.route == "LIMIT_ORDER", limit

market = dispatcher.dispatch(
    {
        "symbol": "BRM6@RTSX",
        "side": "BUY",
        "qty": 1,
        "order_route": "REAL_EXECUTION",
        "price": 102.8,
    },
    {"last": 102.8},
)
assert market.status == "DRY_RUN_ACCEPTED", market
assert market.route == "REAL_EXECUTION", market

bad = dispatcher.dispatch(
    {
        "symbol": "BRM6@RTSX",
        "side": "BUY",
        "qty": 1,
        "order_route": "STOP_ORDER",
    },
    {"last": 102.8},
)
assert bad.status == "REJECTED", bad
assert bad.reason == "missing_stop_price", bad

print("EXECUTION_DISPATCHER_OK")
PY
