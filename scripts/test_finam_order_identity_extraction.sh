#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/execution/finam_order_identity_extraction.py

python - <<'PY'
from finam_core.execution.finam_order_identity_extraction import FinamOrderIdentityExtraction

raw = {
    "status": "1",
    "order_id": "79280879376",
    "raw": {
        "ack": {
            "raw": {
                "response": '''
order_id: "79280879376"
exec_id: "trd.16512900211.1779162613644868"
status: ORDER_STATUS_FILLED
order {
  client_order_id: "fc1779220141086"
}
'''
            }
        }
    }
}

x = FinamOrderIdentityExtraction().extract(raw)

assert x.broker_order_id == "79280879376"
assert x.broker_exec_id == "trd.16512900211.1779162613644868"
assert x.client_order_id == "fc1779220141086"

print("OK: finam order identity extraction")
PY
