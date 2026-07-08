#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_TRADING_PLAN_PARAMETER_BUILDER_V1 ==="

sql_file="sql/knowledge/trading_plan_parameter_builder_seed_v1.sql"
py_file="src/scripts/trading_plan_parameter_builder_v1.py"

test -f "$sql_file"
test -f "$py_file"

PYTHONPYCACHEPREFIX=/tmp/finam_pycache_trading_plan_parameter_builder \
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
echo "$out" | grep -q "VERDICT=TRADING_PLAN_PARAMETER_BUILDER_V1_READY"

after_edge=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_score_model_v2;")

if [ "$before_edge" != "$after_edge" ]; then
  echo "EDGE_SCORE_V2_CHANGED"
  exit 1
fi

rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.recommendation_execution_context_v1
WHERE source_version='TRADING_PLAN_PARAMETER_BUILDER_V1';
")

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.recommendation_execution_context_v1
WHERE source_version='TRADING_PLAN_PARAMETER_BUILDER_V1'
  AND (
       execution_allowed<>0
    OR runtime_allowed<>0
    OR micro_live_allowed<>0
  );
")

skeleton_prices=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.recommendation_execution_context_v1
WHERE source_version='TRADING_PLAN_PARAMETER_BUILDER_V1'
  AND entry_price=1
  AND invalidation_price=1
  AND target_price=1;
")

missing_evidence=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.recommendation_execution_context_v1
WHERE source_version='TRADING_PLAN_PARAMETER_BUILDER_V1'
  AND (
       NOT evidence_json ? 'profile_code'
    OR NOT evidence_json ? 'entry_evidence'
    OR NOT evidence_json ? 'stop_evidence'
    OR NOT evidence_json ? 'target_evidence'
  );
")

test "$rows" -ge 1
test "$unsafe" = "0"
test "$skeleton_prices" = "0"
test "$missing_evidence" = "0"

echo "trading_plan_parameter_rows=$rows"
echo "unsafe_rows=0"
echo "skeleton_price_rows=0"
echo "missing_evidence_rows=0"
echo "hardcode=0"
echo "edge_score_v2_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TRADING_PLAN_PARAMETER_BUILDER_V1_READY"
echo "VERDICT=TEST_TRADING_PLAN_PARAMETER_BUILDER_V1_OK"
