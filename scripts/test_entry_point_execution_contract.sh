#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from dataclasses import asdict

from finam_core.execution.entry_point_selector import EntryPointSelector
from finam_core.execution.execution_decision_layer import ExecutionDecisionLayer
from finam_core.execution.order_router import OrderRouter

selector = EntryPointSelector(tick_size=0.01, stop_atr_mult=1.5, take_atr_mult=2.0)
decision_layer = ExecutionDecisionLayer()
router = OrderRouter()

intent = {"symbol": "BRM6@RTSX", "side": "BUY", "qty": 1}
st = {"last": 80.0, "atr": 0.5}

enriched = selector.enrich_intent(intent, st)
decision = decision_layer.decide(enriched, st)

assert decision.action == "LIMIT", decision
assert decision.order_type == "LIMIT", decision
assert float(decision.limit_price) == 80.01, decision
assert decision.reason == "entry_point_selected_atr_limit", decision

route_intent = dict(enriched)
route_intent["execution_action"] = decision.action
route_intent["order_type"] = decision.order_type
route_intent["execution_reason"] = decision.reason
route_intent["limit_price"] = decision.limit_price

route = router.route(route_intent, st)

assert route["route"] == "LIMIT_ORDER", route
assert route["order_type"] == "LIMIT", route
assert route["limit_price"] == 80.01, route
assert route["stop_loss"] == 79.26, route
assert route["take_profit"] == 81.01, route
assert route["entry_price"] == 80.01, route

print("ENTRY_POINT_EXECUTION_CONTRACT_OK")
PY
