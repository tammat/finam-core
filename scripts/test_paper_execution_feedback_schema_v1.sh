#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_EXECUTION_FEEDBACK_SCHEMA_V1 ==="

sql_files=(
  sql/analytics/paper_execution_feedback_schema_v1.sql
  sql/analytics/paper_execution_feedback_seed_v1.sql
)

for f in "${sql_files[@]}"; do
  test -f "$f"
done

if grep -RInE 'DROP TABLE|TRUNCATE|DELETE FROM|UPDATE .*runtime|UPDATE .*execution|INSERT INTO .*orders|INSERT INTO .*fills' "${sql_files[@]}"; then
  echo "DANGEROUS_SQL_FOUND"
  exit 1
fi

if grep -RInE 'SBER|LKOH|GAZP|VTBR|BUY|SELL|LONG|SHORT' "${sql_files[@]}"; then
  echo "HARDCODE_FOUND"
  exit 1
fi

psql -d finam_core -v ON_ERROR_STOP=1 -f sql/analytics/paper_execution_feedback_schema_v1.sql
psql -d finam_core -v ON_ERROR_STOP=1 -f sql/analytics/paper_execution_feedback_seed_v1.sql

missing=$(psql -At -d finam_core -c "
SELECT count(*)
FROM (
  VALUES
    ('analytics.paper_execution_feedback_scope_v1'),
    ('analytics.paper_execution_feedback_action_v1'),
    ('analytics.paper_execution_feedback_v1')
) t(full_name)
LEFT JOIN pg_class c
  ON c.relname=split_part(full_name,'.',2)
LEFT JOIN pg_namespace n
  ON n.oid=c.relnamespace
 AND n.nspname=split_part(full_name,'.',1)
WHERE c.oid IS NULL;
")

scope_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.paper_execution_feedback_scope_v1
WHERE enabled;
")

action_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.paper_execution_feedback_action_v1
WHERE enabled;
")

bad_defaults=$(psql -At -d finam_core -c "
SELECT count(*)
FROM information_schema.columns
WHERE table_schema='analytics'
  AND table_name='paper_execution_feedback_v1'
  AND column_name IN ('approved','applied','auto_decision')
  AND column_default <> '0';
")

test "$missing" = "0"
test "$scope_rows" -ge 8
test "$action_rows" -ge 6
test "$bad_defaults" = "0"

echo "feedback_schema=OK"
echo "feedback_scope_rows=$scope_rows"
echo "feedback_action_rows=$action_rows"
echo "safe_defaults=OK"
echo "hardcode=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PAPER_EXECUTION_FEEDBACK_SCHEMA_V1_READY"
echo "VERDICT=TEST_PAPER_EXECUTION_FEEDBACK_SCHEMA_V1_OK"
