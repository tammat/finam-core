#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export BROKER_CATEGORY=KNUR

python - <<'PY'
from finam_core.execution.oco_order_manager import OcoOrderManager


class FakeOrdersClient:
    def __init__(self):
        self.limit_called = False
        self.stop_called = False

    def place_stop_order(self, **kwargs):
        self.stop_called = True
        return {"status": "ACCEPTED", "order_id": "stop_1"}

    def place_limit_order(self, **kwargs):
        self.limit_called = True
        return {"status": "ACCEPTED", "order_id": "limit_1"}

    def cancel_order(self, order_id):
        return {"status": "CANCELED", "order_id": order_id}


client = FakeOrdersClient()
manager = OcoOrderManager(client)

manager.register_group(
    group_id="g1",
    symbol="NGM6@RTSX",
    first_order_id="entry_1",
    second_order_id="entry_2",
    protection_by_order_id={
        "entry_1": {
            "exit_side": "SELL",
            "qty": 1,
            "stop_loss_price": 2.1,
            "take_profit_price": 2.9,
            "instrument_type": "FUTURE",
        }
    },
)

result = manager.handle_order_event({"order_id": "entry_1", "status": "FILLED"})

assert result is not None
assert result.reason == "futures_forbidden", result
assert client.stop_called is False
assert client.limit_called is False

client2 = FakeOrdersClient()
manager2 = OcoOrderManager(client2)

manager2.register_group(
    group_id="g2",
    symbol="SBER@MISX",
    first_order_id="entry_1",
    second_order_id="entry_2",
    protection_by_order_id={
        "entry_1": {
            "exit_side": "SELL",
            "qty": 1,
            "stop_loss_price": 290,
            "take_profit_price": 320,
            "instrument_type": "STOCK",
        }
    },
)

result2 = manager2.handle_order_event({"order_id": "entry_1", "status": "FILLED"})

assert result2 is not None
assert result2.status == "TRIGGERED", result2
assert result2.reason == "other_order_cancelled_and_protection_placed", result2
assert client2.stop_called is True
assert client2.limit_called is True

print("OK: OCO BrokerCapabilitiesGate protects futures and allows stock EXIT sell")
PY
