#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/execution/broker_event_idempotency.py

grep -q "duplicate_broker_event" \
  src/finam_core/execution/broker_event_idempotency.py

grep -q "broker_event_idempotency" \
  src/finam_core/execution/broker_event_idempotency.py

grep -q "build_event_key" \
  src/finam_core/execution/broker_event_idempotency.py

echo "OK: broker event idempotency"
