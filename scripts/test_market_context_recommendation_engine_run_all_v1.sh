#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_CONTEXT_RECOMMENDATION_ENGINE_RUN_ALL_V1 ==="

file="src/marketcore/recommendation/engine.py"
test -f "$file"

PYTHONPYCACHEPREFIX=/tmp/finam_pycache_recommendation_engine \
PYTHONPATH=src \
python -m py_compile "$file"

if grep -RInE 'send_order|place_order|cancel_order|execute_order|INSERT INTO .*orders|INSERT INTO .*fills|UPDATE .*runtime|UPDATE .*execution|UPDATE .*edge_score_model_v2|DELETE FROM|DROP TABLE|TRUNCATE' "$file"; then
  echo "DANGEROUS_CODE_FOUND"
  exit 1
fi

if grep -RInE "SBER|LKOH|VTBR|GAZP|BUY|SELL|LONG|SHORT|80|70|60|50|0\.70|0\.80|0\.90" "$file"; then
  echo "HARDCODE_FOUND"
  exit 1
fi

before_edge=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_score_model_v2;")

out=$(PYTHONPATH=src python "$file")
echo "$out"
echo "$out" | grep -q "VERDICT=MARKET_CONTEXT_RECOMMENDATION_ENGINE_RUN_ALL_V1_READY"

after_edge=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_score_model_v2;")

if [ "$before_edge" != "$after_edge" ]; then
  echo "EDGE_SCORE_V2_ROWCOUNT_CHANGED"
  exit 1
fi

coverage=$(psql -At -d finam_core -c "
WITH edge_targets AS (
  SELECT count(DISTINCT symbol || '|' || timeframe) AS total
  FROM knowledge.edge_context_v1
  WHERE source_version='MARKETCORE_MARKET_KNOWLEDGE_EDGE_CONTEXT_BRIDGE_V1'
),
recommended AS (
  SELECT count(DISTINCT symbol || '|' || timeframe) AS total
  FROM knowledge.recommendation_result_v1
)
SELECT round(100.0 * recommended.total / nullif(edge_targets.total,0), 2)
FROM edge_targets, recommended;
")

echo "recommendation_coverage_pct=$coverage"

python3 - <<PY
coverage=float("${coverage}")
if coverage < 100.0:
    raise SystemExit("RECOMMENDATION_COVERAGE_NOT_FULL")
PY

echo "business_logic_source=postgres"
echo "hardcode=0"
echo "edge_score_v2_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKET_CONTEXT_RECOMMENDATION_ENGINE_RUN_ALL_V1_READY"
echo "VERDICT=TEST_MARKET_CONTEXT_RECOMMENDATION_ENGINE_RUN_ALL_V1_OK"
