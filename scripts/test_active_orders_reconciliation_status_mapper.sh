#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.reconciliation.active_orders_reconciliation import map_broker_order_status

assert map_broker_order_status({"status": "WORKING"}) == "ACCEPTED"
assert map_broker_order_status({"orderStatus": "MATCHED"}) == "FILLED"
assert map_broker_order_status({"state": "REJECTED"}) == "REJECTED"
assert map_broker_order_status({"order_state": "CANCELLED"}) == "CANCELLED"

class Obj:
    status = "ORDER_STATUS_WORKING"

assert map_broker_order_status(Obj()) == "ACCEPTED"

print("ACTIVE_ORDERS_RECONCILIATION_STATUS_MAPPER_OK")
PY
