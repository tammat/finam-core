#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export ENABLE_ENGINE_COORDINATOR_EXECUTION_ROUTE=1

python -m py_compile \
  src/finam_core/engine/trading_engine_coordinator.py \
  src/finam_core/execution/execution_gateway.py \
  src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
import os

from finam_core.engine.trading_engine_coordinator import TradingEngineCoordinator


class MockGateway:
    def __init__(self):
        self.called = False

    def route(self, intent, state):
        self.called = True
        routed = dict(intent)
        routed["order_route"] = "MARKET_ORDER"
        routed["routed_by"] = "mock_gateway"
        routed["price"] = state.get("price")
        return routed


gateway = MockGateway()
coordinator = TradingEngineCoordinator(execution_gateway=gateway)

intent = {
    "symbol": "BRM6@RTSX",
    "side": "BUY",
    "qty": 1,
}

state = {
    "symbol": "BRM6@RTSX",
    "price": 100.0,
}

routed = coordinator.route_execution(intent, state)

assert os.getenv("ENABLE_ENGINE_COORDINATOR_EXECUTION_ROUTE") == "1"
assert gateway.called is True
assert routed["symbol"] == "BRM6@RTSX"
assert routed["side"] == "BUY"
assert routed["qty"] == 1
assert routed["order_route"] == "MARKET_ORDER"
assert routed["routed_by"] == "mock_gateway"
assert routed["price"] == 100.0

print("OK: engine coordinator execution route runtime path")
PY
