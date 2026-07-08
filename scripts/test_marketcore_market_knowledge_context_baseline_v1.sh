#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_MARKET_KNOWLEDGE_CONTEXT_BASELINE_V1 ==="

file="src/scripts/market_knowledge_context_baseline_v1.py"
bridge="src/scripts/market_knowledge_edge_context_bridge_v1.py"

test -f "$file"
test -f "$bridge"

PYTHONPYCACHEPREFIX=/tmp/finam_pycache_mk_context_baseline \
PYTHONPATH=src \
python -m py_compile "$file" "$bridge"

if grep -RInE 'send_order|place_order|cancel_order|execute_order|INSERT INTO .*orders|INSERT INTO .*fills|UPDATE .*runtime|UPDATE .*execution|UPDATE .*edge_score_model_v2|DELETE FROM|DROP TABLE|TRUNCATE' "$file" "$bridge"; then
  echo "DANGEROUS_CODE_FOUND"
  exit 1
fi

before_edge=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_score_model_v2;")

out=$(PYTHONPYCACHEPREFIX=/tmp/finam_pycache_mk_context_baseline PYTHONPATH=src python "$file")
echo "$out"

after_edge=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_score_model_v2;")

if [ "$before_edge" != "$after_edge" ]; then
  echo "EDGE_SCORE_V2_ROWCOUNT_CHANGED before=$before_edge after=$after_edge"
  exit 1
fi

echo "$out" | grep -q "VERDICT=MARKETCORE_MARKET_KNOWLEDGE_CONTEXT_BASELINE_V1_READY"
echo "$out" | grep -q "edge_score_v2_changed=0"
echo "$out" | grep -q "runtime_changed=0"
echo "$out" | grep -q "execution_changed=0"
echo "$out" | grep -q "orders_changed=0"
echo "$out" | grep -q "fills_changed=0"
echo "$out" | grep -q "micro_live_allowed=0"

baseline_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.market_context_v1
WHERE source_version='MARKETCORE_MARKET_KNOWLEDGE_CONTEXT_BASELINE_V1';
")

if [ "$baseline_rows" -lt 1 ]; then
  echo "NO_BASELINE_CONTEXT_ROWS"
  exit 1
fi

missing_unknown=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.market_context_v1
WHERE source_version='MARKETCORE_MARKET_KNOWLEDGE_CONTEXT_BASELINE_V1'
  AND regime_code <> 'UNKNOWN';
")

if [ "$missing_unknown" != "0" ]; then
  echo "NON_UNKNOWN_BASELINE_CONTEXT_ROWS=$missing_unknown"
  exit 1
fi

# Пересобираем bridge после появления baseline context.
bridge_out=$(PYTHONPYCACHEPREFIX=/tmp/finam_pycache_mk_context_baseline PYTHONPATH=src python "$bridge")
echo "$bridge_out"

echo "$bridge_out" | grep -q "VERDICT=MARKETCORE_MARKET_KNOWLEDGE_EDGE_CONTEXT_BRIDGE_V1_READY"

bridge_with_context=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.edge_context_v1
WHERE source_version='MARKETCORE_MARKET_KNOWLEDGE_EDGE_CONTEXT_BRIDGE_V1'
  AND context_id IS NOT NULL;
")

if [ "$bridge_with_context" -lt 1 ]; then
  echo "NO_EDGE_CONTEXT_ROWS_WITH_CONTEXT_ID"
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

echo "baseline_context_rows=$baseline_rows"
echo "edge_context_rows_with_context_id=$bridge_with_context"
echo "unsafe_recommendation_rows=0"
echo "destructive_sql=0"
echo "edge_score_v2_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_MARKETCORE_MARKET_KNOWLEDGE_CONTEXT_BASELINE_V1_OK"
