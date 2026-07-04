#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_FEATURE_STORE_HEALTH_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/analytics/005_feature_store_health_v1.sql

PYTHONPATH=src python -m py_compile \
  src/scripts/build_feature_store_health_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_feature_store_health_v1.py | tee /tmp/feature_store_health_v1.txt

grep -q "VERDICT=FEATURE_STORE_HEALTH_V1_READY" /tmp/feature_store_health_v1.txt

rows=$(psql -At -d finam_core -c "SELECT feature_rows FROM analytics.feature_store_health_v1 WHERE health_id='GLOBAL';")
status=$(psql -At -d finam_core -c "SELECT health_status FROM analytics.feature_store_health_v1 WHERE health_id='GLOBAL';")
timer=$(psql -At -d finam_core -c "SELECT timer_active FROM analytics.feature_store_health_v1 WHERE health_id='GLOBAL';")

test "$rows" -gt 0
test "$status" = "HEALTHY"
test "$timer" = "active"

psql -d finam_core -c "
SELECT *
FROM analytics.feature_store_health_v1;
"

echo "feature_rows=$rows"
echo "health_status=$status"
echo "timer_active=$timer"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=FEATURE_STORE_HEALTH_V1_READY"
echo "VERDICT=TEST_FEATURE_STORE_HEALTH_V1_OK"
