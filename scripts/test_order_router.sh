#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.execution.order_router import OrderRouter

r = OrderRouter()

market = r.route(
    {"symbol": "BRM6@RTSX", "side": "BUY", "qty": 1, "execution_action": "MARKET", "price": 103.4},
    {"last": 103.4},
)
assert market["route"] == "REAL_EXECUTION", market
assert market["order_type"] == "MARKET", market

stop = r.route(
    {"symbol": "BRM6@RTSX", "side": "BUY", "qty": 1, "execution_action": "STOP", "stop_price": 103.2},
    {"last": 102.8},
)
assert stop["route"] == "STOP_ORDER", stop
assert stop["stop_price"] == 103.2, stop

limit = r.route(
    {"symbol": "BRM6@RTSX", "side": "BUY", "qty": 1, "execution_action": "LIMIT", "limit_price": 102.1},
    {"last": 102.8},
)
assert limit["route"] == "LIMIT_ORDER", limit
assert limit["limit_price"] == 102.1, limit

bad = r.route(
    {"symbol": "BRM6@RTSX", "side": "BUY", "qty": 1, "execution_action": "STOP"},
    {"last": 102.8},
)
assert bad["route"] == "SKIP", bad
assert bad["reason"] == "missing_stop_price", bad

print("ORDER_ROUTER_OK")
PY
