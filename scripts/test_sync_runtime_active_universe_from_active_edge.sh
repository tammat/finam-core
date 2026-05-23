#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile src/scripts/sync_runtime_active_universe_from_active_edge.py

grep -q "ng_active_edge_state" src/scripts/sync_runtime_active_universe_from_active_edge.py
grep -q "active_edge_block" src/scripts/sync_runtime_active_universe_from_active_edge.py
grep -q "SYNC_RUNTIME_ACTIVE_UNIVERSE_FROM_ACTIVE_EDGE_OK" src/scripts/sync_runtime_active_universe_from_active_edge.py

echo "TEST_SYNC_RUNTIME_ACTIVE_UNIVERSE_FROM_ACTIVE_EDGE_OK"
