#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export EXECUTION_MODE=real
export REAL_EXECUTION_ENABLED=0
export REAL_ORDER_CONFIRM=0
export ENABLE_EXECUTION_DECISION_LAYER=1
export ENABLE_ORDER_ROUTER=1

python - <<'PY'
from finam_core.execution.entry_point_selector import EntryPointSelector
from finam_core.execution.execution_decision_layer import ExecutionDecisionLayer
from finam_core.execution.order_router import OrderRouter
from finam_core.execution.execution_dispatcher import ExecutionDispatcher
from finam_core.adapters.grpc.orders_client import FinamOrdersClient

selector = EntryPointSelector(tick_size=0.01, stop_atr_mult=1.5, take_atr_mult=2.0)
decision_layer = ExecutionDecisionLayer()
router = OrderRouter()
dispatcher = ExecutionDispatcher(orders_client=FinamOrdersClient())

intent = {"symbol": "BRM6@RTSX", "side": "BUY", "qty": 1, "signal_type": "pullback"}
st = {"last": 80.0, "atr": 0.5}

enriched = selector.enrich_intent(intent, st)
decision = decision_layer.decide(enriched, st)

route_intent = dict(enriched)
route_intent["execution_action"] = decision.action
route_intent["execution_reason"] = decision.reason
route_intent["order_type"] = decision.order_type
route_intent["limit_price"] = decision.limit_price

route = router.route(route_intent, st)
assert route["route"] == "LIMIT_ORDER", route

res = dispatcher.place_limit_order(
    symbol=route["symbol"],
    side=route["side"],
    qty=route["qty"],
    limit_price=route["limit_price"],
)

assert res["status"] == "DRY_RUN_ACCEPTED", res

print("LIMIT_ENTRY_FULL_CHAIN_DRY_RUN_OK")
PY
