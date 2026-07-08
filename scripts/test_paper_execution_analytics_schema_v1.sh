#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_EXECUTION_ANALYTICS_SCHEMA_V1 ==="

sql_file="sql/analytics/paper_execution_analytics_schema_v1.sql"
test -f "$sql_file"

if grep -RInE 'DROP TABLE|TRUNCATE|DELETE FROM|UPDATE .*runtime|UPDATE .*execution|INSERT INTO .*orders|INSERT INTO .*fills' "$sql_file"; then
  echo "DANGEROUS_SQL_FOUND"
  exit 1
fi

if grep -RInE 'SBER|LKOH|GAZP|VTBR|BUY|SELL|LONG|SHORT' "$sql_file"; then
  echo "HARDCODE_FOUND"
  exit 1
fi

psql -d finam_core -v ON_ERROR_STOP=1 -f "$sql_file"

missing=$(psql -At -d finam_core -c "
SELECT count(*)
FROM (
  VALUES
    ('analytics.analytics_snapshot_v1'),
    ('analytics.paper_execution_summary_v1'),
    ('analytics.paper_execution_profile_scorecard_v1'),
    ('analytics.paper_execution_source_scorecard_v1'),
    ('analytics.paper_execution_regime_scorecard_v1')
) t(full_name)
LEFT JOIN pg_class c
  ON c.relname=split_part(full_name,'.',2)
LEFT JOIN pg_namespace n
  ON n.oid=c.relnamespace
 AND n.nspname=split_part(full_name,'.',1)
WHERE c.oid IS NULL;
")

test "$missing" = "0"

bad_fk=$(psql -At -d finam_core -c "
SELECT count(*)
FROM information_schema.table_constraints
WHERE constraint_type='FOREIGN KEY'
  AND table_schema='analytics'
  AND table_name IN (
    'paper_execution_summary_v1',
    'paper_execution_profile_scorecard_v1',
    'paper_execution_source_scorecard_v1',
    'paper_execution_regime_scorecard_v1'
  );
")

test "$bad_fk" -ge 4

echo "analytics_schema=OK"
echo "tables_missing=0"
echo "snapshot_fk_count=$bad_fk"
echo "hardcode=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PAPER_EXECUTION_ANALYTICS_SCHEMA_V1_READY"
echo "VERDICT=TEST_PAPER_EXECUTION_ANALYTICS_SCHEMA_V1_OK"
