#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export ENABLE_BROKER_RECONCILIATION_GATE=1

python - <<'PY'
from finam_core.pipelines.paper_pipeline import PaperTradingPipeline
from finam_core.execution.broker_reconciliation import BrokerReconciliationEngine


class DummyPipeline:
    _reconciliation_allows_real_order = PaperTradingPipeline._reconciliation_allows_real_order


p = DummyPipeline()
p.broker_reconciliation = BrokerReconciliationEngine()
p._broker_position_qty_by_symbol = {"BRM6@RTSX": 3.0}
p._trading_halt_reason = None

ok, reason = p._reconciliation_allows_real_order("BRM6@RTSX", 2.0)

assert ok is False, (ok, reason)
assert "broker_desync" in reason, reason
assert p._trading_halt_reason is not None

p._broker_position_qty_by_symbol = {"BRM6@RTSX": 2.0}
p._trading_halt_reason = None

ok, reason = p._reconciliation_allows_real_order("BRM6@RTSX", 2.0)

assert ok is True, (ok, reason)
assert reason == "RECONCILIATION_OK", reason

print("BROKER_RECONCILIATION_PIPELINE_GATE_OK")
PY
