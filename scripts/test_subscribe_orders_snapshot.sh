#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export ENABLE_SUBSCRIBE_ORDERS_LISTENER=1
export SUBSCRIBE_ORDERS_MAX_EVENTS_PER_POLL=10

python - <<'PY'
from finam_core.pipelines.paper_pipeline import PaperTradingPipeline


class DummyOrdersClient:
    def subscribe_orders(self, max_events=None):
        return [
            {
                "order_id": "stop_1",
                "symbol": "BRM6@RTSX",
                "side": "SELL",
                "status": "WATCHING",
                "order_type": "STOP",
                "qty": 1.0,
                "stop_price": "101.5",
            },
            {
                "order_id": "stop_1",
                "symbol": "BRM6@RTSX",
                "side": "SELL",
                "status": "CANCELED",
                "order_type": "STOP",
                "qty": 1.0,
                "stop_price": "101.5",
            },
        ]


class DummyPipeline:
    _apply_broker_order_event_to_snapshot = PaperTradingPipeline._apply_broker_order_event_to_snapshot
    _poll_subscribe_orders_once_if_enabled = PaperTradingPipeline._poll_subscribe_orders_once_if_enabled

    def __init__(self):
        self.orders_client = DummyOrdersClient()
        self._broker_orders_by_symbol = {}


p = DummyPipeline()
p._poll_subscribe_orders_once_if_enabled()

assert p._broker_orders_by_symbol == {}, p._broker_orders_by_symbol

p._apply_broker_order_event_to_snapshot(
    {
        "order_id": "stop_2",
        "symbol": "BRM6@RTSX",
        "side": "SELL",
        "status": "WATCHING",
        "order_type": "STOP",
        "qty": 1.0,
        "stop_price": "102.0",
    }
)

assert len(p._broker_orders_by_symbol["BRM6@RTSX"]) == 1, p._broker_orders_by_symbol

print("SUBSCRIBE_ORDERS_SNAPSHOT_OK")
PY
