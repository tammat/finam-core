#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/research/build_br_edge_decomposition_v1.py

grep -q "trade_context_snapshots" src/scripts/research/build_br_edge_decomposition_v1.py
grep -q "trade_attribution_v2" src/scripts/research/build_br_edge_decomposition_v1.py
grep -q "BR_EDGE_DECOMPOSITION_V1_OK" src/scripts/research/build_br_edge_decomposition_v1.py

echo "BR_EDGE_DECOMPOSITION_V1_TEST_OK"
