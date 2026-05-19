#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/run_runtime_recovery_coordinator_v2.py

grep -q "RUNTIME_RECOVERY_COORDINATOR_V2_OK" \
  src/scripts/run_runtime_recovery_coordinator_v2.py

grep -q "recovery_reserved_timeout" \
  src/scripts/run_runtime_recovery_coordinator_v2.py

grep -q "recovery_stale_sent_ack" \
  src/scripts/run_runtime_recovery_coordinator_v2.py

echo "OK: runtime recovery coordinator v2"
