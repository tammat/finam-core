#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile src/scripts/run_continuous_runtime_governance.py

grep -q "RUNTIME_GOVERNANCE_CYCLE_START" src/scripts/run_continuous_runtime_governance.py
grep -q "build_ng_live_runtime_state.py" src/scripts/run_continuous_runtime_governance.py
grep -q "sync_runtime_active_universe_from_ng_live_state.py" src/scripts/run_continuous_runtime_governance.py

echo "TEST_CONTINUOUS_RUNTIME_GOVERNANCE_OK"
