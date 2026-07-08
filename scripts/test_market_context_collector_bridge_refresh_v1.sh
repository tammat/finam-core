#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_CONTEXT_COLLECTOR_BRIDGE_REFRESH_V1 ==="

collector="src/scripts/market_context_collector_v1.py"
bridge="src/scripts/market_knowledge_edge_context_bridge_v1.py"

test -f "$collector"
test -f "$bridge"

PYTHONPYCACHEPREFIX=/tmp/finam_pycache_context_bridge_refresh \
PYTHONPATH=src \
python -m py_compile "$collector" "$bridge"

if grep -RInE 'send_order|place_order|cancel_order|execute_order|INSERT INTO .*orders|INSERT INTO .*fills|UPDATE .*runtime|UPDATE .*execution|UPDATE .*edge_score_model_v2|DELETE FROM|DROP TABLE|TRUNCATE' "$collector" "$bridge"; then
  echo "DANGEROUS_CODE_FOUND"
  exit 1
fi

before_edge=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_score_model_v2;")

collector_out=$(PYTHONPYCACHEPREFIX=/tmp/finam_pycache_context_bridge_refresh PYTHONPATH=src python "$collector")
echo "$collector_out"
echo "$collector_out" | grep -q "VERDICT=MARKET_CONTEXT_COLLECTOR_V1_READY"

bridge_out=$(PYTHONPYCACHEPREFIX=/tmp/finam_pycache_context_bridge_refresh PYTHONPATH=src python "$bridge")
echo "$bridge_out"
echo "$bridge_out" | grep -q "VERDICT=MARKETCORE_MARKET_KNOWLEDGE_EDGE_CONTEXT_BRIDGE_V1_READY"

after_edge=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_score_model_v2;")

if [ "$before_edge" != "$after_edge" ]; then
  echo "EDGE_SCORE_V2_ROWCOUNT_CHANGED before=$before_edge after=$after_edge"
  exit 1
fi

context_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.market_context_v1
WHERE source_version='MARKET_CONTEXT_COLLECTOR_V1';
")

bridge_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.edge_context_v1
WHERE source_version='MARKETCORE_MARKET_KNOWLEDGE_EDGE_CONTEXT_BRIDGE_V1';
")

bridge_with_context=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.edge_context_v1
WHERE source_version='MARKETCORE_MARKET_KNOWLEDGE_EDGE_CONTEXT_BRIDGE_V1'
  AND context_id IS NOT NULL;
")

if [ "$context_rows" -lt 1 ]; then
  echo "NO_CONTEXT_ROWS"
  exit 1
fi

if [ "$bridge_rows" -lt 1 ]; then
  echo "NO_BRIDGE_ROWS"
  exit 1
fi

if [ "$bridge_with_context" -lt 1 ]; then
  echo "NO_BRIDGE_ROWS_WITH_CONTEXT_ID"
  exit 1
fi

unsafe_reco=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.recommendation_v1
WHERE execution_allowed <> 0
   OR runtime_allowed <> 0
   OR micro_live_allowed <> 0;
")

if [ "$unsafe_reco" != "0" ]; then
  echo "UNSAFE_RECOMMENDATION_ROWS=$unsafe_reco"
  exit 1
fi

echo "context_rows=$context_rows"
echo "bridge_rows=$bridge_rows"
echo "bridge_rows_with_context_id=$bridge_with_context"
echo "unsafe_recommendation_rows=0"
echo "destructive_sql=0"
echo "edge_score_rows_before=$before_edge"
echo "edge_score_rows_after=$after_edge"
echo "edge_score_v2_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKET_CONTEXT_COLLECTOR_BRIDGE_REFRESH_V1_READY"
echo "VERDICT=TEST_MARKET_CONTEXT_COLLECTOR_BRIDGE_REFRESH_V1_OK"
