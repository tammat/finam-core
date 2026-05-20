#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/run_runtime_recovery_integration.py

grep -q "run_sending_intent_recovery.py" src/scripts/run_runtime_recovery_integration.py
grep -q "run_client_order_id_recovery_lookup.py" src/scripts/run_runtime_recovery_integration.py
grep -q "run_real_order_state_synchronizer.py" src/scripts/run_runtime_recovery_integration.py
grep -q "run_oms_invariant_audit.py" src/scripts/run_runtime_recovery_integration.py
grep -q "run_execution_correctness_audit.py" src/scripts/run_runtime_recovery_integration.py
grep -q "RUNTIME_RECOVERY_INTEGRATION_OK" src/scripts/run_runtime_recovery_integration.py

echo "OK: runtime recovery integration"
