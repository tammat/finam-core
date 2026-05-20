#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/run_startup_execution_recovery_chain.py

grep -q "STARTUP_RECOVERY_STEP_BEGIN" \
  src/scripts/run_startup_execution_recovery_chain.py

grep -q "STARTUP_EXECUTION_RECOVERY_CHAIN_OK" \
  src/scripts/run_startup_execution_recovery_chain.py

grep -q "run_sending_intent_recovery.py" \
  src/scripts/run_startup_execution_recovery_chain.py

grep -q "run_real_order_state_synchronizer.py" \
  src/scripts/run_startup_execution_recovery_chain.py

echo "OK: startup execution recovery chain"
