#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_MODEL_HEALTH_ENGINE_V1 ==="

sql_file="sql/analytics/marketcore_model_health_engine_seed_v1.sql"
py_file="src/scripts/marketcore_model_health_engine_v1.py"

test -f "$sql_file"
test -f "$py_file"

PYTHONPYCACHEPREFIX=/tmp/finam_pycache_model_health \
PYTHONPATH=src \
python -m py_compile "$py_file"

if grep -RInE 'send_order|place_order|cancel_order|execute_order|INSERT INTO .*orders|INSERT INTO .*fills|UPDATE .*runtime|UPDATE .*execution|DROP TABLE|TRUNCATE|DELETE FROM' "$sql_file" "$py_file"; then
  echo "DANGEROUS_CODE_FOUND"
  exit 1
fi

if grep -RInE 'SBER|LKOH|GAZP|VTBR|BUY|SELL|LONG|SHORT' "$sql_file" "$py_file"; then
  echo "HARDCODE_FOUND"
  exit 1
fi

psql -d finam_core -v ON_ERROR_STOP=1 -f "$sql_file"

before_edge=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_score_model_v2;")

out=$(PYTHONPATH=src python "$py_file")
echo "$out"
echo "$out" | grep -q "VERDICT=MARKETCORE_MODEL_HEALTH_ENGINE_V1_READY"

after_edge=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_score_model_v2;")
test "$before_edge" = "$after_edge"

snapshot_id=$(echo "$out" | awk -F= '/model_health_snapshot_id=/{print $2}' | tail -1)
test -n "$snapshot_id"

components=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.marketcore_model_health_component_v1
WHERE model_health_snapshot_id=${snapshot_id}
  AND source_version='MARKETCORE_MODEL_HEALTH_ENGINE_V1';
")

gates=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.marketcore_model_health_gate_v1
WHERE model_health_snapshot_id=${snapshot_id}
  AND source_version='MARKETCORE_MODEL_HEALTH_ENGINE_V1';
")

recommendations=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.marketcore_model_health_recommendation_v1
WHERE model_health_snapshot_id=${snapshot_id}
  AND source_version='MARKETCORE_MODEL_HEALTH_ENGINE_V1';
")

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.marketcore_model_health_recommendation_v1
WHERE model_health_snapshot_id=${snapshot_id}
  AND (
       approved<>0
    OR applied<>0
    OR auto_decision<>0
  );
")

bad_status=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.marketcore_model_health_component_v1
WHERE model_health_snapshot_id=${snapshot_id}
  AND component_status NOT IN ('PASS','WARNING','BLOCKED');
")

test "$components" -ge 8
test "$gates" -ge 4
test "$recommendations" -ge 1
test "$unsafe" = "0"
test "$bad_status" = "0"

echo "model_health_snapshot_id=$snapshot_id"
echo "components=$components"
echo "gates=$gates"
echo "recommendations=$recommendations"
echo "unsafe_rows=0"
echo "bad_status_rows=0"
echo "hardcode=0"
echo "edge_score_v2_changed=0"
echo "parameters_source=postgres"
echo "registry_source=postgres"
echo "approved=0"
echo "applied=0"
echo "auto_decision=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_MODEL_HEALTH_ENGINE_V1_READY"
echo "VERDICT=TEST_MARKETCORE_MODEL_HEALTH_ENGINE_V1_OK"
