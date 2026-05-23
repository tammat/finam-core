#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile src/scripts/sync_runtime_active_universe_from_ng_live_state.py

grep -q "ng_live_runtime_state" src/scripts/sync_runtime_active_universe_from_ng_live_state.py
grep -q "runtime_state = 'ACTIVE'" src/scripts/sync_runtime_active_universe_from_ng_live_state.py
grep -q "SYNC_RUNTIME_ACTIVE_UNIVERSE_FROM_NG_LIVE_STATE_OK" src/scripts/sync_runtime_active_universe_from_ng_live_state.py

echo "TEST_SYNC_RUNTIME_ACTIVE_UNIVERSE_FROM_NG_LIVE_STATE_OK"
