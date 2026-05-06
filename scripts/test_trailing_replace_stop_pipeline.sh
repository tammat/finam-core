#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export REAL_EXECUTION_ENABLED=0
export REAL_ORDER_CONFIRM=0

python - <<'PY'
from dataclasses import dataclass
from finam_core.pipelines.paper_pipeline import PaperTradingPipeline


@dataclass
class Decision:
    action: str
    symbol: str
    side: str
    qty: float
    stop_price: float
    reason: str = "test_replace_stop"


class DummyCancelReplaceManager:
    def __init__(self):
        self.calls = []

    def replace_stop(self, *, symbol, old_order_id, side, qty, stop_price):
        self.calls.append((symbol, old_order_id, side, qty, stop_price))

        class Result:
            new_order_id = "new_stop_1"
            status = "DRY_RUN_ACCEPTED"
            reason = None

        return Result()


class DummyPipeline:
    _handle_trailing_replace_stop_decision = PaperTradingPipeline._handle_trailing_replace_stop_decision

    def __init__(self):
        self.cancel_replace_stop_manager = DummyCancelReplaceManager()
        self._broker_orders_by_symbol = {
            "BRM6@RTSX": [
                {
                    "order_id": "old_stop_1",
                    "symbol": "BRM6@RTSX",
                    "side": "SELL",
                    "status": "WATCHING",
                    "order_type": "STOP",
                    "qty": 1.0,
                    "stop_price": 101.5,
                }
            ]
        }


p = DummyPipeline()

p._handle_trailing_replace_stop_decision(
    Decision(
        action="REPLACE_STOP",
        symbol="BRM6@RTSX",
        side="SELL",
        qty=1.0,
        stop_price=102.1,
    )
)

assert p.cancel_replace_stop_manager.calls == [
    ("BRM6@RTSX", "old_stop_1", "SELL", 1.0, 102.1)
], p.cancel_replace_stop_manager.calls



class DummyPipelineNoStop:
    _handle_trailing_replace_stop_decision = PaperTradingPipeline._handle_trailing_replace_stop_decision

    def __init__(self):
        self.cancel_replace_stop_manager = DummyCancelReplaceManager()
        self._broker_orders_by_symbol = {
            "BRM6@RTSX": [
                {
                    "order_id": "limit_1",
                    "symbol": "BRM6@RTSX",
                    "side": "SELL",
                    "status": "WATCHING",
                    "order_type": "LIMIT",
                    "qty": 1.0,
                    "price": 105.0,
                }
            ]
        }


p_no_stop = DummyPipelineNoStop()

p_no_stop._handle_trailing_replace_stop_decision(
    Decision(
        action="REPLACE_STOP",
        symbol="BRM6@RTSX",
        side="SELL",
        qty=1.0,
        stop_price=102.1,
    )
)

assert p_no_stop.cancel_replace_stop_manager.calls == [], p_no_stop.cancel_replace_stop_manager.calls

print("TRAILING_REPLACE_STOP_PIPELINE_OK")
print("TRAILING_REPLACE_STOP_PIPELINE_NEGATIVE_OK")
PY
