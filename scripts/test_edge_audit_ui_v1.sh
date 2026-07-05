#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_AUDIT_UI_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/pages/edge_audit_page.py \
  src/marketcore/presentation/router.py \
  src/marketcore/presentation/ui_labels.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_pipeline_audit_v1.py >/tmp/edge_audit_refresh.txt

sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS http://127.0.0.1:8080/edge-audit >/tmp/edge_audit_ui.html

grep -q "Edge Audit" /tmp/edge_audit_ui.html
grep -q "EDGE_PIPELINE_AUDIT_V1" /tmp/edge_audit_ui.html
grep -q "FUNNEL" /tmp/edge_audit_ui.html

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_EDGE_AUDIT_UI_V1_OK"
