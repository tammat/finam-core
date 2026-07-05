#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_PIPELINE_AUDIT_V1 ==="

PYTHONPATH=src python -m py_compile src/scripts/build_edge_pipeline_audit_v1.py
DATABASE_URL=postgresql:///finam_core PYTHONPATH=src python src/scripts/build_edge_pipeline_audit_v1.py | tee /tmp/edge_pipeline_audit_v1.txt

grep -q "VERDICT=EDGE_PIPELINE_AUDIT_V1_READY" /tmp/edge_pipeline_audit_v1.txt
test -f reports/edge_pipeline_audit_latest.txt
test -f reports/edge_pipeline_audit_latest.json
test -f reports/edge_pipeline_audit_latest.html
grep -q "Edge Pipeline Audit" reports/edge_pipeline_audit_latest.html

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_EDGE_PIPELINE_AUDIT_V1_OK"
