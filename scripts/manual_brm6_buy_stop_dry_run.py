# -*- coding: utf-8 -*-
from __future__ import annotations

import os

from finam_core.execution.execution_decision_layer import ExecutionDecisionLayer
from finam_core.execution.order_router import OrderRouter
from finam_core.execution.execution_dispatcher import ExecutionDispatcher
from finam_core.adapters.grpc.orders_client import FinamOrdersClient


assert os.getenv("EXECUTION_MODE") == "real_dry_run", "EXECUTION_MODE must be real_dry_run"
assert os.getenv("REAL_ORDER_CONFIRM") == "0", "REAL_ORDER_CONFIRM must be 0 for safe dry-run"

intent = {
    "symbol": "BRM6@RTSX",
    "side": "BUY",
    "qty": 1,
    "signal_type": "breakout",
    "breakout_level": 103.20,
    "price": 102.80,
}

market_state = {
    "symbol": "BRM6@RTSX",
    "last": 102.80,
    "bid": 102.79,
    "ask": 102.81,
    "atr": 0.50,
}

decision = ExecutionDecisionLayer().decide(intent, market_state)
print("DECISION", decision)

routed_intent = dict(intent)
routed_intent["execution_action"] = decision.action
routed_intent["order_type"] = decision.order_type
routed_intent["execution_reason"] = decision.reason

if decision.stop_price is not None:
    routed_intent["stop_price"] = decision.stop_price
if decision.limit_price is not None:
    routed_intent["limit_price"] = decision.limit_price

route = OrderRouter().route(routed_intent, market_state)
print("ROUTE", route)

dispatcher = ExecutionDispatcher(
    orders_client=FinamOrdersClient(),
    real_execution_engine=None,
)

result = dispatcher.dispatch(route, market_state)
print("DISPATCH", result)

assert result.route == "STOP_ORDER", result
assert result.status == "DRY_RUN_ACCEPTED", result
assert result.symbol == "BRM6@RTSX", result
assert result.side == "BUY", result
assert float(result.qty) == 1.0, result

print("FINAL_BRM6_BUY_STOP_DRY_RUN_OK")
