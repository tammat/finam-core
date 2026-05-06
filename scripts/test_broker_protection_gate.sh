#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export ENABLE_BROKER_PROTECTION_GATE=1

python - <<'PY'
from finam_core.pipelines.paper_pipeline import PaperTradingPipeline


class DummyPipeline:
    _broker_protection_gate_allows_order = PaperTradingPipeline._broker_protection_gate_allows_order

    def __init__(self):
        self._broker_position_qty_by_symbol = {}
        self._broker_orders_by_symbol = {}


p = DummyPipeline()

ok, reason = p._broker_protection_gate_allows_order("BRM6@RTSX", "BUY", 0)
assert ok, reason

p._broker_position_qty_by_symbol = {"BRM6@RTSX": 1.0}
p._broker_orders_by_symbol = {"BRM6@RTSX": []}

ok, reason = p._broker_protection_gate_allows_order("BRM6@RTSX", "BUY", 1)
assert not ok, reason
assert "broker_position_unprotected" in reason, reason

ok, reason = p._broker_protection_gate_allows_order("BRM6@RTSX", "SELL", 1)
assert ok, reason

p._broker_orders_by_symbol = {
    "BRM6@RTSX": [
        {
            "order_id": "stop_1",
            "side": "SELL",
            "status": "WATCHING",
            "order_type": "STOP",
            "qty": 1.0,
            "stop_price": 100.0,
        }
    ]
}

ok, reason = p._broker_protection_gate_allows_order("BRM6@RTSX", "BUY", 1)
assert ok, reason

print("BROKER_PROTECTION_GATE_OK")
PY
