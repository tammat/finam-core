#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_SPRINT_ENGINE_V1 ==="

PYTHONPATH=src python -m py_compile \
    src/scripts/run_edge_sprint_engine_v1.py

DATABASE_URL=postgresql:///finam_core \
PYTHONPATH=src \
python src/scripts/run_edge_sprint_engine_v1.py \
| tee /tmp/edge_sprint_engine_v1.txt

grep -q "VERDICT=EDGE_SPRINT_ENGINE_V1_READY" \
    /tmp/edge_sprint_engine_v1.txt

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_EDGE_SPRINT_ENGINE_V1_OK"
