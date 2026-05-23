#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile src/scripts/build_ng_active_edge_resolver.py

grep -q "ng_active_edge_state" src/scripts/build_ng_active_edge_resolver.py
grep -q "active_edge" src/scripts/build_ng_active_edge_resolver.py
grep -q "NG_ACTIVE_EDGE_STATE_SUMMARY" src/scripts/build_ng_active_edge_resolver.py

echo "TEST_NG_ACTIVE_EDGE_RESOLVER_OK"
