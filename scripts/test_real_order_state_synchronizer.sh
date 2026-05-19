#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/execution/real_order_state_synchronizer.py \
  src/scripts/run_real_order_state_synchronizer.py

python - <<'PY'
from finam_core.execution.real_order_state_synchronizer import RealOrderStateSynchronizer

s = RealOrderStateSynchronizer()

assert s.map_broker_status(broker_status="ACTIVE").intent_state == "ACK"
assert s.map_broker_status(broker_status="PARTIALLY_FILLED").intent_state == "PARTIAL_FILL"
assert s.map_broker_status(broker_status="FILLED").intent_state == "FILLED"
assert s.map_broker_status(broker_status="CANCELLED").intent_state == "CANCELLED"
assert s.map_broker_status(broker_status="REJECTED").intent_state == "REJECTED"

print("OK: real order state synchronizer")
PY
