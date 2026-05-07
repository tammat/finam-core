#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.execution.oco_order_manager import OcoOrderManager


class DummyOrdersClient:
    def __init__(self):
        self.cancelled = []

    def cancel_order(self, order_id):
        self.cancelled.append(order_id)
        return {"status": "DRY_RUN_CANCEL", "order_id": order_id}

    def place_stop_order(self, symbol, side, qty, stop_price):
        return {
            "status": "DRY_RUN_ACCEPTED",
            "order_id": f"sl_{symbol}_{side}_{qty}_{stop_price}",
        }

    def place_limit_order(self, symbol, side, qty, limit_price):
        return {
            "status": "DRY_RUN_ACCEPTED",
            "order_id": f"tp_{symbol}_{side}_{qty}_{limit_price}",
        }


client = DummyOrdersClient()
mgr = OcoOrderManager(client)

group = mgr.register_group(
    group_id="oco_br_1",
    symbol="BRM6@RTSX",
    first_order_id="buy_stop_103_20",
    second_order_id="sell_stop_101_00",
    protection_by_order_id={
        "buy_stop_103_20": {
            "exit_side": "SELL",
            "qty": 1,
            "stop_loss_price": 102.2,
            "take_profit_price": 105.0,
        },
        "sell_stop_101_00": {
            "exit_side": "BUY",
            "qty": 1,
            "stop_loss_price": 101.8,
            "take_profit_price": 99.0,
        },
    },
)

assert group.status == "ACTIVE", group
assert mgr.get_group("oco_br_1") is group

# Нейтральный статус не должен отменять вторую заявку.
r = mgr.handle_order_event({"order_id": "buy_stop_103_20", "status": "WATCHING"})
assert r.status == "ACTIVE", r
assert client.cancelled == [], client.cancelled

# Исполнение первой заявки отменяет вторую.
r = mgr.handle_order_event({"order_id": "buy_stop_103_20", "status": "FILLED"})
assert r.status == "TRIGGERED", r
assert r.triggered_order_id == "buy_stop_103_20", r
assert r.canceled_order_id == "sell_stop_101_00", r
assert client.cancelled == ["sell_stop_101_00"], client.cancelled
assert r.stop_loss_order_id == "sl_BRM6@RTSX_SELL_1.0_102.2", r
assert r.take_profit_order_id == "tp_BRM6@RTSX_SELL_1.0_105.0", r

# Повтор события не должен повторно отменять.
r = mgr.handle_order_event({"order_id": "buy_stop_103_20", "status": "FILLED"})
assert r.status == "TRIGGERED", r
assert client.cancelled == ["sell_stop_101_00"], client.cancelled

# Чужая заявка игнорируется.
r = mgr.handle_order_event({"order_id": "unknown", "status": "FILLED"})
assert r is None, r

print("OCO_ORDER_MANAGER_OK")
PY
