#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/run_oms_invariant_audit.py

grep -q "FILLED_WITHOUT_BROKER_ORDER_ID" \
  src/scripts/run_oms_invariant_audit.py

grep -q "FILLED_WITHOUT_EXECUTED_QTY" \
  src/scripts/run_oms_invariant_audit.py

grep -q "DUPLICATE_FILLED_ORDER" \
  src/scripts/run_oms_invariant_audit.py

grep -q "OMS_INVARIANT_AUDIT_OK" \
  src/scripts/run_oms_invariant_audit.py

echo "OK: OMS invariant audit"
