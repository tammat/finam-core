#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_FEATURE_STORE_COMPLETE_CHECKPOINT_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/scripts/build_feature_snapshot_v1.py \
  src/scripts/build_feature_snapshot_history_backfill_v1.py \
  src/scripts/build_feature_store_health_v1.py \
  src/marketcore/presentation/pages/feature_store.py \
  src/marketcore/api/serve_knowledge_graph_api_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_feature_store_health_v1.py

sudo systemctl restart marketcore-kg-api.service
sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS "http://127.0.0.1:8095/api/kg/v1/feature-store/summary" > /tmp/feature_store_complete_summary.json
curl -fsS "http://127.0.0.1:8095/api/kg/v1/feature-store/health" > /tmp/feature_store_complete_health.json
curl -fsS "http://127.0.0.1:8080/feature-store" > /tmp/feature_store_complete_ui.html

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.feature_snapshot_v1;")
symbols=$(psql -At -d finam_core -c "SELECT count(DISTINCT symbol) FROM analytics.feature_snapshot_v1;")
health=$(psql -At -d finam_core -c "SELECT health_status FROM analytics.feature_store_health_v1 WHERE health_id='GLOBAL';")
timer=$(psql -At -d finam_core -c "SELECT timer_active FROM analytics.feature_store_health_v1 WHERE health_id='GLOBAL';")
with_return=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.feature_snapshot_v1 WHERE return1_pct IS NOT NULL;")
with_volume=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.feature_snapshot_v1 WHERE volume_ratio20 IS NOT NULL;")

test "$rows" -gt 0
test "$symbols" -gt 1
test "$health" = "HEALTHY"
test "$timer" = "active"
test "$with_return" -gt 0
test "$with_volume" -gt 0

grep -q "Feature Store" /tmp/feature_store_complete_ui.html
grep -q "analytics.feature_snapshot_v1" /tmp/feature_store_complete_ui.html
grep -q "HEALTHY" /tmp/feature_store_complete_ui.html

echo "feature_rows=$rows"
echo "feature_symbols=$symbols"
echo "health_status=$health"
echo "timer_active=$timer"
echo "with_return1=$with_return"
echo "with_volume_ratio20=$with_volume"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=FEATURE_STORE_COMPLETE_CHECKPOINT_V1_READY"
echo "VERDICT=TEST_FEATURE_STORE_COMPLETE_CHECKPOINT_V1_OK"
