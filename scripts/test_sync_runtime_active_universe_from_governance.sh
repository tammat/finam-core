#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile src/scripts/sync_runtime_active_universe_from_governance.py

grep -q "runtime_governance_decisions" src/scripts/sync_runtime_active_universe_from_governance.py
grep -q "runtime_active_universe" src/scripts/sync_runtime_active_universe_from_governance.py
grep -q "SYNC_RUNTIME_ACTIVE_UNIVERSE_FROM_GOVERNANCE_OK" src/scripts/sync_runtime_active_universe_from_governance.py

echo "TEST_SYNC_RUNTIME_ACTIVE_UNIVERSE_FROM_GOVERNANCE_OK"
