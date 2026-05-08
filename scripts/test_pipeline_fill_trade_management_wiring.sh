#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export TRADE_MANAGEMENT_ENABLED=1
export STOP_REPLACE_LIVE=0

python - <<'PY'
from finam_core.pipelines.paper_pipeline import PaperTradingPipeline
from finam_core.execution.trade_management_service import TradeManagementService
from finam_core.execution.fill_event_router import FillEventRouter

class DummyPipeline:
    pass

p = DummyPipeline()
p.fill_event_router = FillEventRouter(TradeManagementService())
p._subscribe_orders_last_error = None

method = PaperTradingPipeline._handle_trade_management_fill_event_if_enabled

event = {
    "symbol": "BRM6",
    "status": "FILLED",
    "side": "BUY",
    "qty": 1,
    "client_order_id": "BRM6_TP1",
    "stop_order_id": "old-stop-br",
}

method(p, event)
method(p, event)

assert p._subscribe_orders_last_error is None

print("PIPELINE_FILL_TRADE_MANAGEMENT_WIRING_OK")
PY
