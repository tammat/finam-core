#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/run_execution_correctness_audit.py

grep -q "EXECUTION_CORRECTNESS_AUDIT_OK" src/scripts/run_execution_correctness_audit.py
grep -q "EXECUTION_CORRECTNESS_AUDIT_FAIL" src/scripts/run_execution_correctness_audit.py
grep -q "SENT_WITHOUT_BROKER_ORDER_ID" src/scripts/run_execution_correctness_audit.py
grep -q "FILLED_QTY_MISMATCH" src/scripts/run_execution_correctness_audit.py

echo "OK: execution correctness audit"
