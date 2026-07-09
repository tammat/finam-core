#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_SIGNAL_FUNNEL_ANALYTICS_V1 ==="

sql_file="sql/analytics/signal_funnel_analytics_v1.sql"
py_file="src/scripts/signal_funnel_analytics_v1.py"
report="reports/signal_funnel_analytics_v1.txt"

mkdir -p reports

psql -d finam_core -v ON_ERROR_STOP=1 -f "$sql_file"

PYTHONPYCACHEPREFIX=/tmp/finam_pycache_signal_funnel \
PYTHONPATH=src \
python -m py_compile "$py_file"

if grep -RInE 'send_order|place_order|cancel_order|execute_order|UPDATE .*runtime|UPDATE .*execution|INSERT INTO .*orders|INSERT INTO .*fills|DROP TABLE|TRUNCATE|DELETE FROM' "$sql_file" "$py_file"; then
  echo "DANGEROUS_CODE_FOUND"
  exit 1
fi

out=$(PYTHONPATH=src python "$py_file")
echo "$out"
echo "$out" | grep -q "VERDICT=SIGNAL_FUNNEL_ANALYTICS_V1_READY"

snapshot_id=$(echo "$out" | awk -F= '/signal_funnel_snapshot_id=/{print $2}' | tail -1)
test -n "$snapshot_id"

rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.signal_funnel_stage_v1
WHERE signal_funnel_snapshot_id=${snapshot_id}
  AND source_version='SIGNAL_FUNNEL_ANALYTICS_V1';
")

bad_status=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.signal_funnel_stage_v1
WHERE signal_funnel_snapshot_id=${snapshot_id}
  AND stage_status NOT IN ('OK','ZERO','BOTTLENECK');
")

test "$rows" -ge 8
test "$bad_status" = "0"

{
echo "======================================================"
echo "SIGNAL FUNNEL ANALYTICS V1"
echo "======================================================"
echo "snapshot_id=${snapshot_id}"
echo
psql -d finam_core -P pager=off -c "
SELECT
  stage_order,
  stage_code,
  stage_name,
  stage_count,
  previous_stage_count,
  pass_rate_pct,
  stage_status
FROM analytics.signal_funnel_stage_v1
WHERE signal_funnel_snapshot_id=${snapshot_id}
ORDER BY stage_order;
"
echo
echo "VERDICT=SIGNAL_FUNNEL_ANALYTICS_V1_READY"
} | tee "$report"

echo "signal_funnel_rows=$rows"
echo "bad_status_rows=0"
echo "report=$report"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=SIGNAL_FUNNEL_ANALYTICS_V1_READY"
echo "VERDICT=TEST_SIGNAL_FUNNEL_ANALYTICS_V1_OK"
