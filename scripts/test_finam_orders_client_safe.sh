#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export EXECUTION_MODE=real
unset REAL_ORDER_CONFIRM

python - <<'PY'
from finam_core.adapters.grpc.orders_client import FinamOrdersClient
from finam_core.execution.real_execution import RealExecutionEngine

client = FinamOrdersClient()
engine = RealExecutionEngine(client)

res = engine.execute({
    "symbol": "BRM6@RTSX",
    "side": "BUY",
    "qty": 1,
    "price": 110.5,
})

assert res.status == "REJECTED", res
assert res.reason in (
    "FINAM_ACCOUNT_ID_not_set",
    "FINAM_TOKEN_not_set",
    "REAL_ORDER_CONFIRM_not_enabled",
), res

print("FINAM_ORDERS_CLIENT_SAFE_OK")
PY

PYTHONPATH=src ${PYTHON_BIN:-python} - <<'PY'
from finam_core.adapters.grpc.orders_client import FinamOrdersClient
from finam_proto.grpc.tradeapi.v1.orders import orders_service_pb2
from finam_proto.grpc.tradeapi.v1 import side_pb2

c = FinamOrdersClient()
order = c._build_stop_order("BRM6@RTSX", "SELL", 3, 110.20)

assert order.symbol == "BRM6@RTSX", order
assert order.side == side_pb2.SIDE_SELL, order
assert order.type == orders_service_pb2.ORDER_TYPE_STOP, order
assert order.stop_condition == orders_service_pb2.STOP_CONDITION_LAST_DOWN, order
assert order.time_in_force == orders_service_pb2.TIME_IN_FORCE_DAY, order
assert order.valid_before == orders_service_pb2.VALID_BEFORE_END_OF_DAY, order
assert order.stop_price.value.startswith("110.2"), order

print("FINAM_STOP_ORDER_BUILD_OK")
PY
