#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/run_production_checkpoint_execution_v2.py

grep -q "run_runtime_recovery_integration.py" src/scripts/run_production_checkpoint_execution_v2.py
grep -q "run_oms_invariant_audit.py" src/scripts/run_production_checkpoint_execution_v2.py
grep -q "run_execution_correctness_audit.py" src/scripts/run_production_checkpoint_execution_v2.py
grep -q "PRODUCTION_CHECKPOINT_EXECUTION_V2_OK" src/scripts/run_production_checkpoint_execution_v2.py

echo "OK: production checkpoint execution v2"
