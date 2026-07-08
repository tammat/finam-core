#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_CONTEXT_QUALITY_AUDIT_V1 ==="

mkdir -p reports
report="reports/market_context_quality_audit_v1.txt"

{
echo "=== MARKET_CONTEXT_QUALITY_AUDIT_V1 ==="
echo "generated_at=$(date -Is)"
echo

echo "=== MARKET CONTEXT ROWS BY SOURCE ==="
psql -d finam_core -P pager=off -c "
SELECT source_version, count(*) AS rows_total
FROM knowledge.market_context_v1
GROUP BY source_version
ORDER BY rows_total DESC, source_version;
"

echo
echo "=== MARKET CONTEXT UNKNOWN COVERAGE ==="
psql -d finam_core -P pager=off -c "
SELECT
    count(*) AS rows_total,
    sum((regime_code='UNKNOWN')::int) AS regime_unknown,
    sum((volatility_state='UNKNOWN')::int) AS volatility_unknown,
    sum((liquidity_state='UNKNOWN')::int) AS liquidity_unknown,
    sum((volume_state='UNKNOWN')::int) AS volume_unknown,
    sum((spread_state='UNKNOWN')::int) AS spread_unknown,
    sum((correlation_state='UNKNOWN')::int) AS correlation_unknown,
    sum((sector_strength_state='UNKNOWN')::int) AS sector_strength_unknown,
    sum((session_state='UNKNOWN')::int) AS session_unknown
FROM knowledge.market_context_v1
WHERE source_version='MARKET_CONTEXT_COLLECTOR_V1';
"

echo
echo "=== MARKET CONTEXT BY SYMBOL ==="
psql -d finam_core -P pager=off -c "
SELECT
    symbol,
    timeframe,
    count(*) AS rows_total,
    max(created_at) AS last_created_at,
    max(regime_code) AS latest_regime_code,
    max(volatility_state) AS latest_volatility_state,
    max(liquidity_state) AS latest_liquidity_state,
    max(session_state) AS latest_session_state
FROM knowledge.market_context_v1
WHERE source_version='MARKET_CONTEXT_COLLECTOR_V1'
GROUP BY symbol, timeframe
ORDER BY symbol, timeframe;
"

echo
echo "=== EDGE CONTEXT BRIDGE QUALITY ==="
psql -d finam_core -P pager=off -c "
SELECT
    count(*) AS bridge_rows,
    sum((context_id IS NOT NULL)::int) AS with_context_id,
    sum((context_id IS NULL)::int) AS without_context_id,
    sum((regime_code='UNKNOWN')::int) AS unknown_regime
FROM knowledge.edge_context_v1
WHERE source_version='MARKETCORE_MARKET_KNOWLEDGE_EDGE_CONTEXT_BRIDGE_V1';
"

echo
echo "=== EDGE CONTEXT LATEST SAMPLE ==="
psql -d finam_core -P pager=off -c "
SELECT symbol, strategy_code, timeframe, regime_code, context_id, edge_score_v2, context_confidence, context_verdict
FROM knowledge.edge_context_v1
WHERE source_version='MARKETCORE_MARKET_KNOWLEDGE_EDGE_CONTEXT_BRIDGE_V1'
ORDER BY created_at DESC
LIMIT 20;
"

echo
echo "=== EVIDENCE SOURCES SAMPLE ==="
psql -d finam_core -P pager=off -c "
SELECT symbol, timeframe, regime_code, evidence_json
FROM knowledge.market_context_v1
WHERE source_version='MARKET_CONTEXT_COLLECTOR_V1'
ORDER BY created_at DESC
LIMIT 20;
"

echo
echo "=== QUALITY FINDINGS ==="
echo "1. If UNKNOWN fields dominate, source tables lack normalized states or column mapping is incomplete."
echo "2. If bridge rows without context_id > 0, bridge source selection must be tightened."
echo "3. Correlation and sector strength are expected UNKNOWN until dedicated engines are implemented."
echo "4. Context confidence is expected 0 in baseline collector."
echo

echo "VERDICT=MARKET_CONTEXT_QUALITY_AUDIT_V1_READY"
} > "$report"

test -s "$report"

if grep -RInE '^[[:space:]]*(DELETE[[:space:]]+FROM|DROP[[:space:]]+TABLE|TRUNCATE[[:space:]]+TABLE|UPDATE[[:space:]]+runtime|UPDATE[[:space:]]+execution|INSERT[[:space:]]+INTO[[:space:]]+.*orders|INSERT[[:space:]]+INTO[[:space:]]+.*fills)' \
  scripts/test_market_context_quality_audit_v1.sh; then
  echo "DESTRUCTIVE_SQL_FOUND"
  exit 1
fi

context_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.market_context_v1
WHERE source_version='MARKET_CONTEXT_COLLECTOR_V1';
")

bridge_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.edge_context_v1
WHERE source_version='MARKETCORE_MARKET_KNOWLEDGE_EDGE_CONTEXT_BRIDGE_V1';
")

bridge_with_context=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.edge_context_v1
WHERE source_version='MARKETCORE_MARKET_KNOWLEDGE_EDGE_CONTEXT_BRIDGE_V1'
  AND context_id IS NOT NULL;
")

if [ "$context_rows" -lt 1 ]; then
  echo "NO_CONTEXT_ROWS"
  exit 1
fi

if [ "$bridge_rows" -lt 1 ]; then
  echo "NO_BRIDGE_ROWS"
  exit 1
fi

if [ "$bridge_with_context" -lt 1 ]; then
  echo "NO_BRIDGE_ROWS_WITH_CONTEXT_ID"
  exit 1
fi

echo "report=$report"
echo "market_context_rows=$context_rows"
echo "edge_context_bridge_rows=$bridge_rows"
echo "bridge_rows_with_context_id=$bridge_with_context"
echo "mode=read_only"
echo "destructive_sql=0"
echo "edge_score_v2_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKET_CONTEXT_QUALITY_AUDIT_V1_READY"
echo "VERDICT=TEST_MARKET_CONTEXT_QUALITY_AUDIT_V1_OK"
