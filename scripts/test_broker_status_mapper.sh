#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.oms.broker_status_mapper import BrokerStatusMapper
from finam_core.oms.order_state_machine import OrderStatus

m = BrokerStatusMapper()

assert m.map_status("NEW").oms_status == OrderStatus.ACCEPTED
assert m.map_status("WORKING").oms_status == OrderStatus.ACCEPTED
assert m.map_status("PENDING_NEW").oms_status == OrderStatus.SENT
assert m.map_status("MATCHED").oms_status == OrderStatus.FILLED
assert m.map_status("PARTIALLY_FILLED").oms_status == OrderStatus.PARTIALLY_FILLED
assert m.map_status("CANCELLED").oms_status == OrderStatus.CANCELLED
assert m.map_status("REJECTED").oms_status == OrderStatus.REJECTED

assert m.map_status("ORDER_STATUS_NEW").oms_status == OrderStatus.ACCEPTED
assert m.map_status("ORDER_STATUS_MATCHED").oms_status == OrderStatus.FILLED
assert m.map_status("ORDER_STATUS_REJECTED").oms_status == OrderStatus.REJECTED

unknown = m.map_status("SOME_NEW_STATUS")
assert unknown.oms_status == OrderStatus.FAILED
assert unknown.reason == "unknown_broker_status:SOME_NEW_STATUS"

missing = m.map_order({"symbol": "NGH6"})
assert missing.oms_status == OrderStatus.FAILED
assert missing.reason == "broker_status_field_missing"

by_status = m.map_order({"status": "WORKING"})
assert by_status.oms_status == OrderStatus.ACCEPTED

by_order_status = m.map_order({"orderStatus": "MATCHED"})
assert by_order_status.oms_status == OrderStatus.FILLED

print("BROKER_STATUS_MAPPER_OK")
PY
