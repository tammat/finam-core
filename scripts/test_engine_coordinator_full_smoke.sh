#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export ENABLE_ENGINE_COORDINATOR_ON_QUOTE=1
export ENABLE_ENGINE_COORDINATOR_RECONCILE=1
export ENABLE_ENGINE_COORDINATOR_EXECUTION_ROUTE=1

python -m py_compile \
  src/finam_core/engine/trading_engine_coordinator.py \
  src/finam_core/portfolio/portfolio_reconciliation_layer.py \
  src/finam_core/execution/execution_gateway.py \
  src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
from finam_core.engine.trading_engine_coordinator import TradingEngineCoordinator


class MockKernel:
    def __init__(self):
        self.events = []

    def process_quote(self, event):
        self.events.append(event)


class MockExecutionGateway:
    def __init__(self):
        self.called = False

    def route(self, intent, state):
        self.called = True
        routed = dict(intent)
        routed["routed_by"] = "mock_execution_gateway"
        routed["price"] = state.get("price")
        return routed


class MockPortfolioReconciliationLayer:
    def __init__(self):
        self.called = False
        self.positions = None
        self.orders = None
        self.context = None

    def run(self, broker_positions=None, broker_orders=None, context=None):
        self.called = True
        self.positions = broker_positions
        self.orders = broker_orders
        self.context = context
        return {"ok": True}


kernel = MockKernel()
gateway = MockExecutionGateway()
reconciliation = MockPortfolioReconciliationLayer()

coordinator = TradingEngineCoordinator(
    pipeline_kernel=kernel,
    execution_gateway=gateway,
    portfolio_reconciliation_layer=reconciliation,
)

quote_result = coordinator.on_quote({"symbol": "BRM6@RTSX", "price": 100.0})
assert quote_result.quote_processed is True, quote_result
assert quote_result.errors == [], quote_result
assert kernel.events == [{"symbol": "BRM6@RTSX", "price": 100.0}]

routed = coordinator.route_execution(
    intent={"symbol": "BRM6@RTSX", "side": "BUY", "qty": 1},
    market_state={"symbol": "BRM6@RTSX", "price": 100.0},
)
assert gateway.called is True
assert routed["symbol"] == "BRM6@RTSX"
assert routed["side"] == "BUY"
assert routed["qty"] == 1
assert routed["price"] == 100.0
assert routed["routed_by"] == "mock_execution_gateway"

reconcile_result = coordinator.reconcile(
    broker_positions=[{"symbol": "BRM6@RTSX", "qty": 0}],
    broker_orders=[{"symbol": "BRM6@RTSX", "orders": []}],
    context={"source": "full_smoke"},
)
assert reconcile_result.reconciliation_processed is True, reconcile_result
assert reconcile_result.errors == [], reconcile_result
assert reconciliation.called is True
assert reconciliation.positions == [{"symbol": "BRM6@RTSX", "qty": 0}]
assert reconciliation.orders == [{"symbol": "BRM6@RTSX", "orders": []}]
assert reconciliation.context == {"source": "full_smoke"}

print("OK: engine coordinator full smoke")
PY
