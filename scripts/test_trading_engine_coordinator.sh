#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/engine/trading_engine_coordinator.py \
  src/finam_core/pipelines/pipeline_kernel.py \
  src/finam_core/execution/execution_gateway.py \
  src/finam_core/portfolio/portfolio_reconciliation_layer.py

python - <<'PY'
from finam_core.engine.trading_engine_coordinator import TradingEngineCoordinator


class MockKernel:
    def __init__(self):
        self.events = []

    def process_quote(self, event):
        self.events.append(event)


class MockExecutionGateway:
    def route(self, intent, state):
        routed = dict(intent)
        routed["routed"] = True
        routed["price"] = state.get("price")
        return routed


class MockReconciliationLayer:
    def __init__(self):
        self.called = False

    def run(self, broker_positions=None, broker_orders=None, context=None):
        self.called = True
        return {"ok": True}


kernel = MockKernel()
gateway = MockExecutionGateway()
reconciliation = MockReconciliationLayer()

coordinator = TradingEngineCoordinator(
    pipeline_kernel=kernel,
    execution_gateway=gateway,
    portfolio_reconciliation_layer=reconciliation,
)

quote_result = coordinator.on_quote({"symbol": "SBER@MISX", "price": 300})
assert quote_result.event == "TRADING_ENGINE_COORDINATOR_QUOTE_RESULT", quote_result
assert quote_result.quote_processed is True, quote_result
assert quote_result.errors == [], quote_result
assert kernel.events == [{"symbol": "SBER@MISX", "price": 300}]

routed = coordinator.route_execution(
    intent={"symbol": "SBER@MISX", "side": "BUY", "qty": 1},
    market_state={"price": 300},
)
assert routed["routed"] is True, routed
assert routed["price"] == 300, routed

reconcile_result = coordinator.reconcile(
    broker_positions=[{"symbol": "SBER@MISX", "qty": 1}],
    broker_orders=[],
    context={"source": "test"},
)
assert reconcile_result.event == "TRADING_ENGINE_COORDINATOR_RECONCILIATION_RESULT", reconcile_result
assert reconcile_result.reconciliation_processed is True, reconcile_result
assert reconcile_result.errors == [], reconcile_result
assert reconciliation.called is True

print("OK: trading engine coordinator")
PY
