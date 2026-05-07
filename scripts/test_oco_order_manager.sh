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

protection = mgr.build_protection_by_order_id(
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

assert protection["buy_stop_103_20"]["exit_side"] == "SELL", protection
assert protection["buy_stop_103_20"]["stop_loss_price"] == 102.20, protection
assert protection["buy_stop_103_20"]["take_profit_price"] == 105.20, protection
assert protection["sell_stop_101_00"]["exit_side"] == "BUY", protection
assert protection["sell_stop_101_00"]["stop_loss_price"] == 102.00, protection
assert protection["sell_stop_101_00"]["take_profit_price"] == 99.00, protection

group = mgr.register_group(
    group_id="oco_br_1",
    symbol="BRM6@RTSX",
    first_order_id="buy_stop_103_20",
    second_order_id="sell_stop_101_00",
    protection_by_order_id=protection,
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
assert r.take_profit_order_id == "tp_BRM6@RTSX_SELL_1.0_105.2", r

# Повтор события не должен повторно отменять.
r = mgr.handle_order_event({"order_id": "buy_stop_103_20", "status": "FILLED"})
assert r.status == "TRIGGERED", r
assert client.cancelled == ["sell_stop_101_00"], client.cancelled

# Чужая заявка игнорируется.
r = mgr.handle_order_event({"order_id": "unknown", "status": "FILLED"})
assert r is None, r

print("OCO_ORDER_MANAGER_OK")
PY
