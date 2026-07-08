#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_CONTEXT_VOLUME_SPREAD_SOURCE_AUDIT_V1 ==="

mkdir -p reports
report="reports/market_context_volume_spread_source_audit_v1.txt"

{
echo "=== MARKET_CONTEXT_VOLUME_SPREAD_SOURCE_AUDIT_V1 ==="
echo "generated_at=$(date -Is)"
echo

for tbl in \
  public.market_snapshot_v1 \
  public.market_bars \
  public.market_ticks \
  public.market_data \
  public.feature_snapshots
do
  echo
  echo "=================================================="
  echo "TABLE=$tbl"
  echo "=================================================="

  schema_name="${tbl%.*}"
  table_name="${tbl#*.}"

  echo "--- EXISTS ---"
  psql -d finam_core -P pager=off -c "SELECT to_regclass('$tbl') AS table_regclass;"

  echo "--- VOLUME/SPREAD/BID/ASK CANDIDATE COLUMNS ---"
  psql -d finam_core -P pager=off -c "
SELECT ordinal_position, column_name, data_type
FROM information_schema.columns
WHERE table_schema='$schema_name'
  AND table_name='$table_name'
  AND (
       column_name ILIKE '%volume%'
    OR column_name ILIKE '%turnover%'
    OR column_name ILIKE '%amount%'
    OR column_name ILIKE '%value%'
    OR column_name ILIKE '%spread%'
    OR column_name ILIKE '%bid%'
    OR column_name ILIKE '%ask%'
    OR column_name ILIKE '%last%'
    OR column_name ILIKE '%close%'
  )
ORDER BY ordinal_position;
"

  echo "--- ROW COUNT ---"
  psql -d finam_core -P pager=off -c "SELECT count(*) AS rows_total FROM $tbl;" 2>/dev/null || echo "ROW_COUNT_UNAVAILABLE"

  echo "--- LATEST SAMPLE ---"
  psql -d finam_core -P pager=off -c "SELECT * FROM $tbl LIMIT 5;" 2>/dev/null || echo "SAMPLE_UNAVAILABLE"
done

echo
echo "=== CURRENT CONTEXT GAP ==="
psql -d finam_core -P pager=off -c "
SELECT
  count(*) AS rows_total,
  sum((volume_state='UNKNOWN')::int) AS volume_unknown,
  sum((spread_state='UNKNOWN')::int) AS spread_unknown,
  sum((liquidity_state='UNKNOWN')::int) AS liquidity_unknown
FROM knowledge.market_context_v1
WHERE source_version='MARKET_CONTEXT_COLLECTOR_V1';
"

echo
echo "=== RECOMMENDED NEXT ACTION ==="
echo "If volume columns exist in market_bars, map volume_state from latest bar volume."
echo "If bid/ask columns exist in market_ticks or market_snapshot_v1, map spread_state from bid/ask."
echo "If no bid/ask/spread exists, keep spread UNKNOWN and mark orderbook requirement."
echo

echo "VERDICT=MARKET_CONTEXT_VOLUME_SPREAD_SOURCE_AUDIT_V1_READY"
} > "$report"

test -s "$report"

if grep -RInE '^[[:space:]]*(DELETE[[:space:]]+FROM|DROP[[:space:]]+TABLE|TRUNCATE[[:space:]]+TABLE|UPDATE[[:space:]]+runtime|UPDATE[[:space:]]+execution|INSERT[[:space:]]+INTO[[:space:]]+.*orders|INSERT[[:space:]]+INTO[[:space:]]+.*fills)' \
  scripts/test_market_context_volume_spread_source_audit_v1.sh; then
  echo "DESTRUCTIVE_SQL_FOUND"
  exit 1
fi

grep -q "MARKET_CONTEXT_VOLUME_SPREAD_SOURCE_AUDIT_V1" "$report"
grep -q "CURRENT CONTEXT GAP" "$report"
grep -q "RECOMMENDED NEXT ACTION" "$report"

echo "report=$report"
echo "mode=read_only"
echo "destructive_sql=0"
echo "edge_score_v2_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKET_CONTEXT_VOLUME_SPREAD_SOURCE_AUDIT_V1_READY"
echo "VERDICT=TEST_MARKET_CONTEXT_VOLUME_SPREAD_SOURCE_AUDIT_V1_OK"
