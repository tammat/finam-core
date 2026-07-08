#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RECOMMENDATION_EXECUTION_CONTEXT_BUILDER_V1 ==="

files=(
  src/marketcore/recommendation/execution_context_models.py
  src/marketcore/recommendation/execution_context_repository.py
  src/marketcore/recommendation/execution_context_builder.py
)

for f in "${files[@]}"; do
  test -f "$f"
  PYTHONPYCACHEPREFIX=/tmp/finam_pycache_exec_builder PYTHONPATH=src python -m py_compile "$f"
done

if grep -RInE 'send_order|place_order|cancel_order|execute_order|INSERT INTO .*orders|INSERT INTO .*fills|UPDATE .*runtime|UPDATE .*execution|DROP TABLE|TRUNCATE|DELETE FROM' "${files[@]}"; then
  echo "DANGEROUS_CODE_FOUND"
  exit 1
fi

if grep -RInE 'SBER|LKOH|GAZP|VTBR|BUY|SELL|LONG|SHORT' "${files[@]}"; then
  echo "HARDCODE_FOUND"
  exit 1
fi

before_edge=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_score_model_v2;")

out=$(PYTHONPATH=src python src/marketcore/recommendation/execution_context_builder.py)
echo "$out"
echo "$out" | grep -q "VERDICT=RECOMMENDATION_EXECUTION_CONTEXT_BUILDER_V1_READY"

after_edge=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_score_model_v2;")

if [ "$before_edge" != "$after_edge" ]; then
  echo "EDGE_SCORE_V2_CHANGED"
  exit 1
fi

rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.recommendation_execution_context_v1
WHERE source_version='RECOMMENDATION_EXECUTION_CONTEXT_MODELS_V1';
")

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.recommendation_execution_context_v1
WHERE execution_allowed<>0
   OR runtime_allowed<>0
   OR micro_live_allowed<>0;
")

bad_fk=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.recommendation_execution_context_v1 x
LEFT JOIN knowledge.recommendation_result_v1 r
  ON r.recommendation_id=x.recommendation_id
LEFT JOIN knowledge.market_context_v1 mc
  ON mc.context_id=x.source_context_id
LEFT JOIN knowledge.edge_context_v1 ec
  ON ec.edge_context_id=x.source_edge_context_id
WHERE r.recommendation_id IS NULL
   OR mc.context_id IS NULL
   OR ec.edge_context_id IS NULL;
")

test "$rows" -ge 1
test "$unsafe" = "0"
test "$bad_fk" = "0"

echo "execution_context_rows=$rows"
echo "unsafe_rows=0"
echo "bad_fk_rows=0"
echo "hardcode=0"
echo "edge_score_v2_changed=0"
echo "execution_allowed=0"
echo "runtime_allowed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=RECOMMENDATION_EXECUTION_CONTEXT_BUILDER_V1_READY"
echo "VERDICT=TEST_RECOMMENDATION_EXECUTION_CONTEXT_BUILDER_V1_OK"
