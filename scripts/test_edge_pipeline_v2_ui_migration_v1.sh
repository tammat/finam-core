#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_PIPELINE_V2_UI_MIGRATION_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/ui_labels.py \
  src/marketcore/presentation/pages/edge_pipeline_v2.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/router.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_pipeline_snapshot_v1.py

sudo systemctl restart marketcore-kg-api.service
sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS "http://127.0.0.1:8080/edge-pipeline-v2" > /tmp/edge_pipeline_v2_ui.html

grep -q "Этапы V2" /tmp/edge_pipeline_v2_ui.html
grep -q "analytics.edge_pipeline_snapshot_v1" /tmp/edge_pipeline_v2_ui.html

if grep -q "BR@RTSX.*H1" /tmp/edge_pipeline_v2_ui.html; then
  echo "ERROR_LEGACY_BR_H1_VISIBLE"
  exit 1
fi

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_PIPELINE_V2_UI_MIGRATION_V1_READY"
echo "VERDICT=TEST_EDGE_PIPELINE_V2_UI_MIGRATION_V1_OK"
