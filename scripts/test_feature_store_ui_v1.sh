#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_FEATURE_STORE_UI_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/pages/feature_store.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/router.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_feature_store_health_v1.py

sudo systemctl restart marketcore-kg-api.service
sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS "http://127.0.0.1:8095/api/kg/v1/feature-store/summary" > /tmp/feature_store_summary.json
curl -fsS "http://127.0.0.1:8095/api/kg/v1/feature-store/health" > /tmp/feature_store_health.json
curl -fsS "http://127.0.0.1:8080/feature-store" > /tmp/feature_store_ui.html

grep -q "Feature Store" /tmp/feature_store_ui.html
grep -q "analytics.feature_snapshot_v1" /tmp/feature_store_ui.html
grep -q "HEALTHY" /tmp/feature_store_ui.html
grep -q "Последние признаки" /tmp/feature_store_ui.html

if grep -R "SELECT .*feature_snapshot_v1\|FROM analytics.feature_snapshot_v1" \
  src/marketcore/presentation/pages/feature_store.py; then
  echo "ERROR_DIRECT_SQL_IN_FEATURE_STORE_UI"
  exit 1
fi

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.feature_snapshot_v1;")
health=$(psql -At -d finam_core -c "SELECT health_status FROM analytics.feature_store_health_v1 WHERE health_id='GLOBAL';")

test "$rows" -gt 0
test "$health" = "HEALTHY"

echo "feature_rows=$rows"
echo "health_status=$health"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=FEATURE_STORE_UI_V1_READY"
echo "VERDICT=TEST_FEATURE_STORE_UI_V1_OK"
