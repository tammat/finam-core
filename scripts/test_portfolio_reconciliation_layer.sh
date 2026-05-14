#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/portfolio/portfolio_reconciliation_layer.py \
  src/finam_core/portfolio/position_portfolio_sync.py

python - <<'PY'
from finam_core.portfolio.portfolio_reconciliation_layer import PortfolioReconciliationLayer


class MockPositionSync:
    def __init__(self):
        self.synced = []

    def sync_position(self, position):
        self.synced.append(position)


class MockOpenOrdersSync:
    def __init__(self):
        self.called = False

    def sync(self, broker_orders=None, context=None):
        self.called = True


class MockRepair:
    def __init__(self):
        self.called = False

    def run(self, context=None):
        self.called = True


position_sync = MockPositionSync()
open_orders_sync = MockOpenOrdersSync()
repair = MockRepair()

layer = PortfolioReconciliationLayer(
    position_sync_layer=position_sync,
    open_orders_sync=open_orders_sync,
    reconciliation_repair=repair,
)

result = layer.run(
    broker_positions=["SBER@MISX", "LKOH@MISX"],
    broker_orders=[{"symbol": "SBER@MISX"}],
    context={"source": "test"},
)

assert result.event == "PORTFOLIO_RECONCILIATION_LAYER_RESULT", result
assert result.positions_synced == 2, result
assert result.open_orders_synced is True, result
assert result.repair_checked is True, result
assert result.errors == [], result
assert position_sync.synced == ["SBER@MISX", "LKOH@MISX"]
assert open_orders_sync.called is True
assert repair.called is True

print("OK: portfolio reconciliation layer")
PY
