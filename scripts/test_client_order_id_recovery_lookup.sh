#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/run_client_order_id_recovery_lookup.py

grep -q "CLIENT_ORDER_ID_RECOVERY_OK" \
  src/scripts/run_client_order_id_recovery_lookup.py

grep -q "client_order_id" \
  src/scripts/run_client_order_id_recovery_lookup.py

grep -q "broker_order_id" \
  src/scripts/run_client_order_id_recovery_lookup.py

grep -q "ExecutionIntentTransitionService" \
  src/scripts/run_client_order_id_recovery_lookup.py

echo "OK: client order id recovery lookup"
