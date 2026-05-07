#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export ENABLE_BROKER_RECONCILIATION_GATE=1

python - <<'PY'
import os

from finam_core.pipelines.paper_pipeline import PaperTradingPipeline
from finam_core.execution.broker_reconciliation import BrokerReconciliationEngine
from finam_core.reconciliation.portfolio_reconciliation_repair import PortfolioReconciliationRepair



class FakeLogger:
    def __init__(self):
        self.events = []

    def log_execution_event(self, **kwargs):
        self.events.append(kwargs)

class FakePM:
    def __init__(self):
        self.sync_called = False
        self.sync_event = None

    def sync_authoritative_position(self, **kwargs):
        self.sync_called = True
        self.sync_event = kwargs
        return {"event": "AUTHORITATIVE_POSITION_SYNC", **kwargs}


pipe = PaperTradingPipeline.__new__(PaperTradingPipeline)
pipe.broker_reconciliation = BrokerReconciliationEngine(qty_tolerance=1e-9)
pipe.portfolio_reconciliation_repair = PortfolioReconciliationRepair(qty_tolerance=1e-9)
pipe._broker_position_qty_by_symbol = {"SBER@MISX": 2.0}
pipe.pm = FakePM()
pipe.pg_logger = FakeLogger()
pipe._trading_halt_reason = None

os.environ["ALLOW_PORTFOLIO_REPAIR"] = "0"
allowed, reason = pipe._reconciliation_allows_real_order("SBER@MISX", local_qty=1.0)

assert allowed is False, (allowed, reason)
assert "broker_desync:SBER@MISX" in reason, reason
assert pipe.pm.sync_called is False

os.environ["ALLOW_PORTFOLIO_REPAIR"] = "1"
allowed, reason = pipe._reconciliation_allows_real_order("SBER@MISX", local_qty=1.0)

assert allowed is True, (allowed, reason)
assert "portfolio_reconciliation_repaired" in reason, reason
assert pipe.pm.sync_called is True
assert pipe.pm.sync_event["symbol"] == "SBER@MISX"
assert pipe.pm.sync_event["qty"] == 2.0
assert pipe.pm.sync_event["source"] == "broker_reconciliation"

print("OK: pipeline reconciliation repair integration")
PY
