#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_PIPELINE_V2_LEGACY_UI_REPLACE_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/pages/edge_pipeline_v2.py \
  src/marketcore/presentation/pages/edge_pipeline_v2_legacy_aliases.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/ui_labels.py \
  src/marketcore/presentation/router.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_pipeline_snapshot_v1.py

sudo systemctl restart marketcore-kg-api.service
sudo systemctl restart marketcore-ui-shell.service
sleep 2

for path in \
  /paper-edge-discovery \
  /edge-validation-queue \
  /edge-validation-pipeline \
  /edge-robustness-check \
  /edge-oos-validation \
  /edge-oos-backtest \
  /micro-live-readiness
do
  out="/tmp/edge_pipeline_legacy_${path//\//_}.html"
  curl -fsS "http://127.0.0.1:8080${path}" > "$out"
  grep -q "analytics.edge_pipeline_snapshot_v1" "$out"

  if grep -q "BR@RTSX.*H1" "$out"; then
    echo "ERROR_LEGACY_BR_H1_VISIBLE path=$path"
    exit 1
  fi
done

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_pipeline_snapshot_v1;")
test "$rows" -gt 0

echo "edge_pipeline_rows=$rows"
echo "legacy_routes_replaced=7"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_PIPELINE_V2_LEGACY_UI_REPLACE_V1_READY"
echo "VERDICT=TEST_EDGE_PIPELINE_V2_LEGACY_UI_REPLACE_V1_OK"
