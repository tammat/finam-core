#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/execution/finam_order_status_adapter.py

python - <<'PY'
from finam_core.execution.finam_order_status_adapter import (
    FinamOrderStatusAdapter,
)

class Client:
    def get_order_status(self, broker_order_id):
        return {
            "status": "FILLED",
            "filled_qty": 1,
            "avg_price": 300,
        }

r = FinamOrderStatusAdapter(Client()).get_status(
    broker_order_id="OID1",
    symbol="SBER@MISX",
)

assert r.ok is True
assert r.broker_status == "FILLED"
assert r.filled_qty == 1
assert r.avg_price == 300

print("OK: finam order status adapter")
PY
