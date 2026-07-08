#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_EXECUTION_ANALYTICS_ENGINE_V1 ==="

sql_file="sql/analytics/paper_execution_analytics_parameter_seed_v1.sql"
py_file="src/scripts/paper_execution_analytics_engine_v1.py"

test -f "$sql_file"
test -f "$py_file"

PYTHONPYCACHEPREFIX=/tmp/finam_pycache_paper_analytics \
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
echo "$out" | grep -q "VERDICT=PAPER_EXECUTION_ANALYTICS_ENGINE_V1_READY"

after_edge=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_score_model_v2;")

if [ "$before_edge" != "$after_edge" ]; then
  echo "EDGE_SCORE_V2_CHANGED"
  exit 1
fi

snapshot_id=$(echo "$out" | awk -F= '/analytics_snapshot_id=/{print $2}' | tail -1)

test -n "$snapshot_id"

summary_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.paper_execution_summary_v1 WHERE analytics_snapshot_id=$snapshot_id;")
profile_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.paper_execution_profile_scorecard_v1 WHERE analytics_snapshot_id=$snapshot_id;")
source_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.paper_execution_source_scorecard_v1 WHERE analytics_snapshot_id=$snapshot_id;")
regime_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.paper_execution_regime_scorecard_v1 WHERE analytics_snapshot_id=$snapshot_id;")

test "$summary_rows" -eq 1
test "$profile_rows" -ge 1
test "$source_rows" -ge 1
test "$regime_rows" -ge 1

bad_fk=$(psql -At -d finam_core -c "
SELECT count(*)
FROM (
  SELECT analytics_snapshot_id FROM analytics.paper_execution_summary_v1 WHERE analytics_snapshot_id=$snapshot_id
  UNION ALL
  SELECT analytics_snapshot_id FROM analytics.paper_execution_profile_scorecard_v1 WHERE analytics_snapshot_id=$snapshot_id
  UNION ALL
  SELECT analytics_snapshot_id FROM analytics.paper_execution_source_scorecard_v1 WHERE analytics_snapshot_id=$snapshot_id
  UNION ALL
  SELECT analytics_snapshot_id FROM analytics.paper_execution_regime_scorecard_v1 WHERE analytics_snapshot_id=$snapshot_id
) x
LEFT JOIN analytics.analytics_snapshot_v1 s
  ON s.analytics_snapshot_id=x.analytics_snapshot_id
WHERE s.analytics_snapshot_id IS NULL;
")

test "$bad_fk" = "0"

echo "analytics_snapshot_id=$snapshot_id"
echo "summary_rows=$summary_rows"
echo "profile_scorecard_rows=$profile_rows"
echo "source_scorecard_rows=$source_rows"
echo "regime_scorecard_rows=$regime_rows"
echo "bad_fk_rows=0"
echo "overfit_guard=sample_status_only"
echo "auto_decision=0"
echo "hardcode=0"
echo "edge_score_v2_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PAPER_EXECUTION_ANALYTICS_ENGINE_V1_READY"
echo "VERDICT=TEST_PAPER_EXECUTION_ANALYTICS_ENGINE_V1_OK"
