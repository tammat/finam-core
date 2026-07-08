#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_CONTEXT_VOLUME_FROM_BARS_PATCH_V1 ==="

files=(
  src/scripts/market_context_collector_v1.py
  src/scripts/market_context_state_inference_v1.py
  src/scripts/market_context_column_map_v1.py
)

for f in "${files[@]}"; do
  test -f "$f"
  PYTHONPYCACHEPREFIX=/tmp/finam_pycache_volume_from_bars PYTHONPATH=src/scripts python -m py_compile "$f"
done

if grep -RInE 'send_order|place_order|cancel_order|execute_order|INSERT INTO .*orders|INSERT INTO .*fills|UPDATE .*runtime|UPDATE .*execution|UPDATE .*edge_score_model_v2|DELETE FROM|DROP TABLE|TRUNCATE' "${files[@]}"; then
  echo "DANGEROUS_CODE_FOUND"
  exit 1
fi

bar_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM public.market_bars WHERE volume IS NOT NULL AND volume > 0;")
if [ "$bar_rows" -lt 1 ]; then
  echo "NO_MARKET_BARS_VOLUME"
  exit 1
fi

before_edge=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_score_model_v2;")

out=$(PYTHONPYCACHEPREFIX=/tmp/finam_pycache_volume_from_bars PYTHONPATH=src/scripts python src/scripts/market_context_collector_v1.py)
echo "$out"
echo "$out" | grep -q "VERDICT=MARKET_CONTEXT_COLLECTOR_V1_READY"

after_edge=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_score_model_v2;")
if [ "$before_edge" != "$after_edge" ]; then
  echo "EDGE_SCORE_V2_ROWCOUNT_CHANGED before=$before_edge after=$after_edge"
  exit 1
fi

coverage=$(psql -At -d finam_core -c "
WITH latest AS (
  SELECT DISTINCT ON (symbol, timeframe)
    symbol,
    timeframe,
    volume_state,
    spread_state,
    evidence_json,
    created_at
  FROM knowledge.market_context_v1
  WHERE source_version='MARKET_CONTEXT_COLLECTOR_V1'
  ORDER BY symbol, timeframe, created_at DESC
)
SELECT
  count(*) || '|' ||
  sum((volume_state <> 'UNKNOWN')::int) || '|' ||
  sum((spread_state <> 'UNKNOWN')::int) || '|' ||
  sum((evidence_json::text ILIKE '%market_bars%')::int)
FROM latest;
")

IFS='|' read -r total volume_known spread_known market_bars_source <<< "$coverage"

echo "latest_context_rows=$total"
echo "volume_known=$volume_known"
echo "spread_known=$spread_known"
echo "market_bars_source_rows=$market_bars_source"

if [ "$total" -lt 1 ]; then
  echo "NO_LATEST_CONTEXT_ROWS"
  exit 1
fi

if [ "$volume_known" -lt 1 ]; then
  echo "VOLUME_FROM_BARS_NOT_APPLIED"
  exit 1
fi

if [ "$market_bars_source" -lt 1 ]; then
  echo "MARKET_BARS_SOURCE_NOT_RECORDED"
  exit 1
fi

echo "volume_from_bars=OK"
echo "spread_requires_bid_ask_or_orderbook=1"
echo "destructive_sql=0"
echo "edge_score_v2_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKET_CONTEXT_VOLUME_FROM_BARS_PATCH_V1_READY"
echo "VERDICT=TEST_MARKET_CONTEXT_VOLUME_FROM_BARS_PATCH_V1_OK"
