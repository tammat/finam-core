#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/run_execution_correctness_repair.py

grep -q "REPAIR_SENT_WITHOUT_BROKER_ORDER_ID" src/scripts/run_execution_correctness_repair.py
grep -q "REPAIR_NEGATIVE_REMAINING_QTY" src/scripts/run_execution_correctness_repair.py
grep -q "REPAIR_FILLED_QTY_MISMATCH" src/scripts/run_execution_correctness_repair.py
grep -q "REPAIR_RUNTIME_FREEZE" src/scripts/run_execution_correctness_repair.py

echo "OK: execution correctness repair"
