#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.adapters.grpc.orders_client import FinamOrdersClient


class Enum:
    @staticmethod
    def Name(v):
        return {
            1: "ORDER_STATUS_WATCHING",
            2: "SIDE_SELL",
            3: "ORDER_TYPE_STOP",
        }.get(int(v), str(v))


class SideEnum:
    @staticmethod
    def Name(v):
        return {2: "SIDE_SELL"}.get(int(v), str(v))


class OrdersPb2:
    OrderStatus = Enum
    OrderType = Enum


class SidePb2:
    Side = SideEnum


class Decimal:
    def __init__(self, value):
        self.value = value


class Order:
    symbol = "BRM6@RTSX"
    side = 2
    type = 3
    quantity = Decimal("1.0")
    limit_price = Decimal("")
    stop_price = Decimal("101.5")


class State:
    order_id = "stop_1"
    exec_id = ""
    status = 1
    order = Order()


c = FinamOrdersClient()
event = c._normalize_order_stream_event(State(), OrdersPb2, SidePb2)

assert event["order_id"] == "stop_1", event
assert event["symbol"] == "BRM6@RTSX", event
assert event["side"] == "SELL", event
assert event["status"] == "WATCHING", event
assert event["order_type"] == "STOP", event
assert event["qty"] == 1.0, event
assert event["stop_price"] == "101.5", event

print("SUBSCRIBE_ORDERS_NORMALIZER_OK")
PY
