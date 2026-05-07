#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export ENABLE_EXECUTION_DECISION_LAYER=1
export ENABLE_ORDER_ROUTER=1
export ENABLE_EXECUTION_DISPATCHER=1

python - <<'PY'
from finam_core.pipelines.paper_pipeline import PaperTradingPipeline
from finam_core.execution.execution_decision_layer import ExecutionDecisionLayer
from finam_core.execution.order_router import OrderRouter
from finam_core.execution.execution_dispatcher import ExecutionDispatcher


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


class DummyPipeline:
    _apply_execution_decision_if_enabled = PaperTradingPipeline._apply_execution_decision_if_enabled
    _route_order_if_enabled = PaperTradingPipeline._route_order_if_enabled
    _dispatch_order_if_enabled = PaperTradingPipeline._dispatch_order_if_enabled

    def __init__(self):
        self.execution_decision_layer = ExecutionDecisionLayer()
        self.order_router = OrderRouter()
        self.execution_dispatcher = ExecutionDispatcher(
            orders_client=DummyOrdersClient(),
            real_execution_engine=None,
        )


p = DummyPipeline()

intent = {
    "symbol": "BRM6@RTSX",
    "side": "BUY",
    "qty": 1,
    "signal_type": "breakout",
    "breakout_level": 103.2,
    "price": 102.8,
}

market_state = {
    "symbol": "BRM6@RTSX",
    "last": 102.8,
    "bid": 102.79,
    "ask": 102.81,
    "atr": 0.5,
}

result = p._dispatch_order_if_enabled(intent, market_state)

assert result is not None, result
assert result.route == "STOP_ORDER", result
assert result.status == "DRY_RUN_ACCEPTED", result
assert result.order_id == "stop_BRM6@RTSX_BUY_1.0_103.2", result

print("EXECUTION_DISPATCHER_PIPELINE_OK")
PY
