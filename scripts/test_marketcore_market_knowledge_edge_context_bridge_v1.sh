#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_MARKET_KNOWLEDGE_EDGE_CONTEXT_BRIDGE_V1 ==="

file="src/scripts/market_knowledge_edge_context_bridge_v1.py"
test -f "$file"

PYTHONPYCACHEPREFIX=/tmp/finam_pycache_mk_edge_bridge \
PYTHONPATH=src \
python -m py_compile "$file"

if grep -RInE 'send_order|place_order|cancel_order|execute_order|INSERT INTO .*orders|INSERT INTO .*fills|UPDATE .*runtime|UPDATE .*execution|UPDATE .*edge_score_model_v2|DELETE FROM|DROP TABLE|TRUNCATE' "$file"; then
  echo "DANGEROUS_CODE_FOUND"
  exit 1
fi

before_edge=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_score_model_v2;")

out=$(PYTHONPYCACHEPREFIX=/tmp/finam_pycache_mk_edge_bridge PYTHONPATH=src python "$file")
echo "$out"

after_edge=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_score_model_v2;")

if [ "$before_edge" != "$after_edge" ]; then
  echo "EDGE_SCORE_V2_ROWCOUNT_CHANGED before=$before_edge after=$after_edge"
  exit 1
fi

echo "$out" | grep -q "VERDICT=MARKETCORE_MARKET_KNOWLEDGE_EDGE_CONTEXT_BRIDGE_V1_READY"
echo "$out" | grep -q "edge_score_v2_changed=0"
echo "$out" | grep -q "runtime_changed=0"
echo "$out" | grep -q "execution_changed=0"
echo "$out" | grep -q "orders_changed=0"
echo "$out" | grep -q "fills_changed=0"
echo "$out" | grep -q "micro_live_allowed=0"

bridge_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.edge_context_v1
WHERE source_version='MARKETCORE_MARKET_KNOWLEDGE_EDGE_CONTEXT_BRIDGE_V1';
")

if [ "$bridge_rows" -lt 1 ]; then
  echo "NO_EDGE_CONTEXT_BRIDGE_ROWS"
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

echo "edge_score_rows_before=$before_edge"
echo "edge_score_rows_after=$after_edge"
echo "edge_context_bridge_rows=$bridge_rows"
echo "unsafe_recommendation_rows=0"
echo "destructive_sql=0"
echo "edge_score_v2_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_MARKETCORE_MARKET_KNOWLEDGE_EDGE_CONTEXT_BRIDGE_V1_OK"
