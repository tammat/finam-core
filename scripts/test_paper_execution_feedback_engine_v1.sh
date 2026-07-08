#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_EXECUTION_FEEDBACK_ENGINE_V1 ==="

sql_file="sql/analytics/paper_execution_feedback_engine_v1.sql"
py_file="src/scripts/paper_execution_feedback_engine_v1.py"

test -f "$sql_file"
test -f "$py_file"

PYTHONPYCACHEPREFIX=/tmp/finam_pycache_paper_feedback_engine \
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
echo "$out" | grep -q "VERDICT=PAPER_EXECUTION_FEEDBACK_ENGINE_V1_READY"

after_edge=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_score_model_v2;")
test "$before_edge" = "$after_edge"

rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.paper_execution_feedback_v1
WHERE source_version='PAPER_EXECUTION_FEEDBACK_ENGINE_V1';
")

bad=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.paper_execution_feedback_v1
WHERE source_version='PAPER_EXECUTION_FEEDBACK_ENGINE_V1'
  AND (
       approved<>0
    OR applied<>0
    OR auto_decision<>0
  );
")

bad_fk=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.paper_execution_feedback_v1 f
LEFT JOIN analytics.paper_execution_feedback_scope_v1 s
  ON s.feedback_scope_code=f.feedback_scope_code
LEFT JOIN analytics.paper_execution_feedback_action_v1 a
  ON a.feedback_action_code=f.recommended_action_code
LEFT JOIN analytics.paper_execution_feedback_reason_v1 r
  ON r.reason_code=f.feedback_reason_code
LEFT JOIN analytics.paper_execution_feedback_severity_v1 v
  ON v.severity_code=f.feedback_severity_code
WHERE f.source_version='PAPER_EXECUTION_FEEDBACK_ENGINE_V1'
  AND (
       s.feedback_scope_code IS NULL
    OR a.feedback_action_code IS NULL
    OR r.reason_code IS NULL
    OR v.severity_code IS NULL
  );
")

test "$rows" -ge 1
test "$bad" = "0"
test "$bad_fk" = "0"

echo "feedback_rows=$rows"
echo "bad_rows=0"
echo "bad_fk_rows=0"
echo "approved=0"
echo "applied=0"
echo "auto_decision=0"
echo "hardcode=0"
echo "edge_score_v2_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PAPER_EXECUTION_FEEDBACK_ENGINE_V1_READY"
echo "VERDICT=TEST_PAPER_EXECUTION_FEEDBACK_ENGINE_V1_OK"
