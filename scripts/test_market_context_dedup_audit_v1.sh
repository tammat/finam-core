#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_CONTEXT_DEDUP_AUDIT_V1 ==="

mkdir -p reports
report="reports/market_context_dedup_audit_v1.txt"

{
echo "=== MARKET_CONTEXT_DEDUP_AUDIT_V1 ==="
echo "generated_at=$(date -Is)"
echo

echo "=== TOTAL ROWS BY SOURCE ==="
psql -d finam_core -P pager=off -c "
SELECT source_version, count(*) AS rows_total
FROM knowledge.market_context_v1
GROUP BY source_version
ORDER BY rows_total DESC, source_version;
"

echo
echo "=== DUPLICATES BY NATURAL KEY ==="
psql -d finam_core -P pager=off -c "
SELECT
  symbol,
  timeframe,
  context_date,
  source_version,
  count(*) AS rows_total,
  min(created_at) AS first_created_at,
  max(created_at) AS last_created_at
FROM knowledge.market_context_v1
WHERE source_version='MARKET_CONTEXT_COLLECTOR_V1'
GROUP BY symbol, timeframe, context_date, source_version
HAVING count(*) > 1
ORDER BY rows_total DESC, symbol, timeframe, context_date;
"

echo
echo "=== LATEST CURRENT CONTEXT PER SYMBOL/TIMEFRAME ==="
psql -d finam_core -P pager=off -c "
SELECT DISTINCT ON (symbol, timeframe)
  symbol,
  timeframe,
  context_date,
  regime_code,
  volatility_state,
  liquidity_state,
  volume_state,
  spread_state,
  session_state,
  correlation_state,
  sector_strength_state,
  created_at
FROM knowledge.market_context_v1
WHERE source_version='MARKET_CONTEXT_COLLECTOR_V1'
ORDER BY symbol, timeframe, created_at DESC;
"

echo
echo "=== DEDUP DECISION OPTIONS ==="
echo "OPTION_A_HISTORY_MODE:"
echo "- Keep all rows."
echo "- Treat market_context_v1 as append-only context snapshot history."
echo "- Coverage reports should use latest DISTINCT ON (symbol, timeframe)."
echo
echo "OPTION_B_CURRENT_STATE_MODE:"
echo "- Add unique key: symbol, timeframe, context_date, source_version."
echo "- Collector should use UPSERT."
echo "- Historical snapshots should move to separate history table later."
echo
echo "RECOMMENDATION:"
echo "- Use OPTION_B for MARKET_CONTEXT_COLLECTOR_V1 current context."
echo "- Keep historical design for a future market_context_history_v1 if needed."
echo

echo "VERDICT=MARKET_CONTEXT_DEDUP_AUDIT_V1_READY"
} > "$report"

test -s "$report"

if grep -RInE '^[[:space:]]*(DELETE[[:space:]]+FROM|DROP[[:space:]]+TABLE|TRUNCATE[[:space:]]+TABLE|UPDATE[[:space:]]+runtime|UPDATE[[:space:]]+execution|INSERT[[:space:]]+INTO[[:space:]]+.*orders|INSERT[[:space:]]+INTO[[:space:]]+.*fills)' \
  scripts/test_market_context_dedup_audit_v1.sh; then
  echo "DESTRUCTIVE_SQL_FOUND"
  exit 1
fi

rows_total=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.market_context_v1
WHERE source_version='MARKET_CONTEXT_COLLECTOR_V1';
")

natural_keys=$(psql -At -d finam_core -c "
SELECT count(*)
FROM (
  SELECT symbol, timeframe, context_date, source_version
  FROM knowledge.market_context_v1
  WHERE source_version='MARKET_CONTEXT_COLLECTOR_V1'
  GROUP BY symbol, timeframe, context_date, source_version
) t;
")

duplicates=$((rows_total - natural_keys))

echo "report=$report"
echo "market_context_rows=$rows_total"
echo "natural_keys=$natural_keys"
echo "duplicate_rows=$duplicates"
echo "mode=read_only"
echo "destructive_sql=0"
echo "edge_score_v2_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKET_CONTEXT_DEDUP_AUDIT_V1_READY"
echo "VERDICT=TEST_MARKET_CONTEXT_DEDUP_AUDIT_V1_OK"
