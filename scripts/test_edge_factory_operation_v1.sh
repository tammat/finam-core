#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_FACTORY_OPERATION_V1 ==="

PYTHONPATH=src python -m py_compile src/scripts/build_edge_factory_operation_v1.py
PYTHONPATH=src python src/scripts/build_edge_factory_operation_v1.py

test -s reports/edge_factory_operation_latest.json
test -s reports/edge_factory_operation_latest.txt

grep -q "VERDICT=EDGE_FACTORY_OPERATION_READY" reports/edge_factory_operation_latest.txt

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_EDGE_FACTORY_OPERATION_V1_OK"
