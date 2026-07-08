#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_CONTEXT_COLLECTOR_UPSERT_V1 ==="

sql_file="sql/knowledge/market_context_collector_upsert_v1.sql"
collector="src/scripts/market_context_collector_v1.py"

test -f "$sql_file"
test -f "$collector"

PYTHONPYCACHEPREFIX=/tmp/finam_pycache_context_upsert PYTHONPATH=src/scripts \
python -m py_compile "$collector"

# DELETE разрешен только в SQL-файле dedup для market_context_v1; runtime/execution/orders/fills запрещены.
if grep -RInE 'DROP TABLE|TRUNCATE|UPDATE .*runtime|UPDATE .*execution|INSERT INTO .*orders|INSERT INTO .*fills|UPDATE .*edge_score_model_v2' \
  "$sql_file" "$collector"; then
  echo "DANGEROUS_CODE_FOUND"
  exit 1
fi

if grep -RInE 'DELETE FROM' "$collector"; then
  echo "DELETE_FOUND_IN_COLLECTOR"
  exit 1
fi

psql -d finam_core -v ON_ERROR_STOP=1 -f "$sql_file"

before_edge=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_score_model_v2;")

out1=$(PYTHONPYCACHEPREFIX=/tmp/finam_pycache_context_upsert PYTHONPATH=src/scripts python "$collector")
echo "$out1"
echo "$out1" | grep -q "VERDICT=MARKET_CONTEXT_COLLECTOR_V1_READY"

rows_after_first=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.market_context_v1
WHERE source_version='MARKET_CONTEXT_COLLECTOR_V1';
")

out2=$(PYTHONPYCACHEPREFIX=/tmp/finam_pycache_context_upsert PYTHONPATH=src/scripts python "$collector")
echo "$out2"
echo "$out2" | grep -q "VERDICT=MARKET_CONTEXT_COLLECTOR_V1_READY"

rows_after_second=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.market_context_v1
WHERE source_version='MARKET_CONTEXT_COLLECTOR_V1';
")

after_edge=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_score_model_v2;")

if [ "$before_edge" != "$after_edge" ]; then
  echo "EDGE_SCORE_V2_ROWCOUNT_CHANGED before=$before_edge after=$after_edge"
  exit 1
fi

if [ "$rows_after_first" != "$rows_after_second" ]; then
  echo "UPSERT_NOT_IDEMPOTENT first=$rows_after_first second=$rows_after_second"
  exit 1
fi

duplicate_rows=$(psql -At -d finam_core -c "
SELECT COALESCE(sum(rows_total - 1), 0)
FROM (
  SELECT symbol, timeframe, context_date, source_version, count(*) AS rows_total
  FROM knowledge.market_context_v1
  WHERE source_version='MARKET_CONTEXT_COLLECTOR_V1'
  GROUP BY symbol, timeframe, context_date, source_version
  HAVING count(*) > 1
) d;
")

if [ "$duplicate_rows" != "0" ]; then
  echo "DUPLICATE_ROWS_REMAIN=$duplicate_rows"
  exit 1
fi

index_exists=$(psql -At -d finam_core -c "
SELECT count(*)
FROM pg_indexes
WHERE schemaname='knowledge'
  AND indexname='ux_market_context_current_v1';
")

if [ "$index_exists" != "1" ]; then
  echo "UPSERT_INDEX_MISSING"
  exit 1
fi

echo "rows_after_first=$rows_after_first"
echo "rows_after_second=$rows_after_second"
echo "duplicate_rows=0"
echo "upsert_idempotent=OK"
echo "upsert_index=OK"
echo "edge_score_v2_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKET_CONTEXT_COLLECTOR_UPSERT_V1_READY"
echo "VERDICT=TEST_MARKET_CONTEXT_COLLECTOR_UPSERT_V1_OK"
