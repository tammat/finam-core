#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export ENABLE_SUBSCRIBE_ORDERS_LISTENER=1
export ENABLE_OCO_ORDER_MANAGER=1

python - <<'PY'
from finam_core.pipelines.paper_pipeline import PaperTradingPipeline
from finam_core.execution.oco_order_manager import OcoOrderManager


class DummyOrdersClient:
    def __init__(self):
        self.cancelled = []

    def subscribe_orders(self, max_events=None):
        return [
            {
                "order_id": "buy_stop_103_20",
                "symbol": "BRM6@RTSX",
                "side": "BUY",
                "status": "FILLED",
                "order_type": "STOP",
                "qty": 1.0,
                "stop_price": "103.20",
            }
        ]

    def cancel_order(self, order_id):
        self.cancelled.append(order_id)
        return {"status": "DRY_RUN_CANCEL", "order_id": order_id}

    def place_stop_order(self, symbol, side, qty, stop_price):
        return {"status": "DRY_RUN_ACCEPTED", "order_id": f"sl_{symbol}_{side}_{qty}_{stop_price}"}

    def place_limit_order(self, symbol, side, qty, limit_price):
        return {"status": "DRY_RUN_ACCEPTED", "order_id": f"tp_{symbol}_{side}_{qty}_{limit_price}"}


class DummyPipeline:
    _apply_broker_order_event_to_snapshot = PaperTradingPipeline._apply_broker_order_event_to_snapshot
    _handle_oco_order_event_if_enabled = PaperTradingPipeline._handle_oco_order_event_if_enabled
    _poll_subscribe_orders_once_if_enabled = PaperTradingPipeline._poll_subscribe_orders_once_if_enabled

    def __init__(self):
        self.orders_client = DummyOrdersClient()
        self._broker_orders_by_symbol = {}
        self.oco_order_manager = OcoOrderManager(self.orders_client)

        protection = self.oco_order_manager.build_protection_by_order_id(
            symbol="BRM6@RTSX",
            first_order_id="buy_stop_103_20",
            first_side="BUY",
            first_entry_price=103.20,
            second_order_id="sell_stop_101_00",
            second_side="SELL",
            second_entry_price=101.00,
            atr=0.50,
            equity=400000,
            risk_pct=0.005,
            stop_atr_mult=2.0,
            reward_risk=2.0,
            max_qty=1,
            tick_size=0.01,
        )

        self.oco_order_manager.register_group(
            group_id="oco_br_1",
            symbol="BRM6@RTSX",
            first_order_id="buy_stop_103_20",
            second_order_id="sell_stop_101_00",
            protection_by_order_id=protection,
        )


p = DummyPipeline()
p._poll_subscribe_orders_once_if_enabled()

group = p.oco_order_manager.get_group("oco_br_1")
assert group.status == "TRIGGERED", group
assert group.triggered_order_id == "buy_stop_103_20", group
assert group.canceled_order_id == "sell_stop_101_00", group
assert group.stop_loss_order_id == "sl_BRM6@RTSX_SELL_1.0_102.2", group
assert group.take_profit_order_id == "tp_BRM6@RTSX_SELL_1.0_105.2", group
assert p.orders_client.cancelled == ["sell_stop_101_00"], p.orders_client.cancelled

print("OCO_SUBSCRIBE_ORDERS_PIPELINE_OK")
PY
