#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_CONTEXT_SOURCE_FORENSIC_AUDIT_V1 ==="

mkdir -p reports
report="reports/market_context_source_forensic_audit_v1.txt"

{
echo "=== MARKET_CONTEXT_SOURCE_FORENSIC_AUDIT_V1 ==="
echo "generated_at=$(date -Is)"
echo

for tbl in \
  public.analytics_regime_snapshots_v2 \
  public.feature_snapshots \
  public.market_snapshot_v1 \
  public.market_event_calendar \
  public.analytics_regime_aware_edge_v1
do
  echo
  echo "=================================================="
  echo "TABLE=$tbl"
  echo "=================================================="

  echo "--- EXISTS ---"
  psql -d finam_core -P pager=off -c "
SELECT to_regclass('$tbl') AS table_regclass;
"

  echo "--- COLUMNS ---"
  schema_name="${tbl%.*}"
  table_name="${tbl#*.}"

  psql -d finam_core -P pager=off -c "
SELECT ordinal_position, column_name, data_type
FROM information_schema.columns
WHERE table_schema='$schema_name'
  AND table_name='$table_name'
ORDER BY ordinal_position;
"

  echo "--- ROW COUNT ---"
  psql -d finam_core -P pager=off -c "
SELECT count(*) AS rows_total
FROM $tbl;
" 2>/dev/null || echo "ROW_COUNT_UNAVAILABLE"

  echo "--- DATE RANGE CANDIDATES ---"
  psql -d finam_core -P pager=off -c "
SELECT
  min(created_at) AS min_created_at,
  max(created_at) AS max_created_at
FROM $tbl;
" 2>/dev/null || echo "CREATED_AT_RANGE_UNAVAILABLE"

  echo "--- SAMPLE LAST 10 ---"
  psql -d finam_core -P pager=off -c "
SELECT *
FROM $tbl
LIMIT 10;
" 2>/dev/null || echo "SAMPLE_UNAVAILABLE"
done

echo
echo "=== FORENSIC QUESTIONS ==="
echo "1. Which table already contains market regime?"
echo "2. Which table already contains volatility/liquidity features?"
echo "3. Which table contains latest market snapshot?"
echo "4. Which table contains calendar/session events?"
echo "5. Which table can feed knowledge.market_context_v1?"
echo

echo "VERDICT=MARKET_CONTEXT_SOURCE_FORENSIC_AUDIT_V1_READY"
} > "$report"

test -s "$report"

if grep -RInE '^[[:space:]]*(DELETE[[:space:]]+FROM|DROP[[:space:]]+TABLE|TRUNCATE[[:space:]]+TABLE|UPDATE[[:space:]]+runtime|UPDATE[[:space:]]+execution|INSERT[[:space:]]+INTO[[:space:]]+.*orders|INSERT[[:space:]]+INTO[[:space:]]+.*fills)' \
  scripts/test_market_context_source_forensic_audit_v1.sh; then
  echo "DESTRUCTIVE_SQL_FOUND"
  exit 1
fi

echo "report=$report"
echo "mode=read_only"
echo "destructive_sql=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKET_CONTEXT_SOURCE_FORENSIC_AUDIT_V1_READY"
echo "VERDICT=TEST_MARKET_CONTEXT_SOURCE_FORENSIC_AUDIT_V1_OK"
