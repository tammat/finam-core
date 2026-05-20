#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/execution/client_order_id_factory.py

python - <<'PY'
from finam_core.execution.client_order_id_factory import build_client_order_id

cid = build_client_order_id(
    strategy="protective_probe",
    symbol="SBER@MISX",
    side="SELL",
)

assert len(cid) <= 20, cid
assert cid.startswith("fc"), cid

print("OK: short client_order_id", cid, len(cid))
PY
