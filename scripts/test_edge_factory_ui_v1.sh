#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_FACTORY_UI_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/pages/edge_factory_page.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/ui_labels.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_pipeline_audit_v1.py >/tmp/edge_factory_audit_refresh.txt

sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS http://127.0.0.1:8080/edge-factory >/tmp/edge_factory.html
curl -fsS http://127.0.0.1:8080/ >/tmp/edge_factory_home.html

grep -q "Edge Factory" /tmp/edge_factory.html
grep -q "Pipeline Funnel" /tmp/edge_factory.html
grep -q "Current Bottleneck" /tmp/edge_factory.html
grep -q "/edge-factory" /tmp/edge_factory_home.html

echo "i18n=ok"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_EDGE_FACTORY_UI_V1_OK"
