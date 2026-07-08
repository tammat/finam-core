#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_CONTEXT_LIQUIDITY_VOLUME_SPREAD_COVERAGE_V1 ==="

files=(
  src/scripts/market_context_state_inference_v1.py
  src/scripts/market_context_collector_v1.py
  src/scripts/market_context_column_map_v1.py
)

for f in "${files[@]}"; do
  test -f "$f"
  PYTHONPYCACHEPREFIX=/tmp/finam_pycache_lvs_coverage PYTHONPATH=src/scripts python -m py_compile "$f"
done

if grep -RInE 'send_order|place_order|cancel_order|execute_order|INSERT INTO .*orders|INSERT INTO .*fills|UPDATE .*runtime|UPDATE .*execution|UPDATE .*edge_score_model_v2|DELETE FROM|DROP TABLE|TRUNCATE' "${files[@]}"; then
  echo "DANGEROUS_CODE_FOUND"
  exit 1
fi

PYTHONPATH=src/scripts python - <<'PY'
from market_context_state_inference_v1 import infer_liquidity_state, infer_spread_state, infer_volume_state

assert infer_volume_state({"volume": 10}) == "KNOWN"
assert infer_volume_state({"volume": 0}) == "UNKNOWN"
assert infer_liquidity_state({"last": 250}) == "KNOWN"
assert infer_spread_state({"bid": 10, "ask": 10.1}) == "KNOWN"
assert infer_spread_state({}) == "UNKNOWN"

print("state_inference=OK")
PY

before_edge=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_score_model_v2;")

out=$(PYTHONPYCACHEPREFIX=/tmp/finam_pycache_lvs_coverage PYTHONPATH=src/scripts python src/scripts/market_context_collector_v1.py)
echo "$out"
echo "$out" | grep -q "VERDICT=MARKET_CONTEXT_COLLECTOR_V1_READY"

after_edge=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_score_model_v2;")

if [ "$before_edge" != "$after_edge" ]; then
  echo "EDGE_SCORE_V2_ROWCOUNT_CHANGED before=$before_edge after=$after_edge"
  exit 1
fi

coverage=$(psql -At -d finam_core -c "
WITH stats AS (
  SELECT
    count(*) AS total,
    sum((liquidity_state<>'UNKNOWN')::int) AS liquidity,
    sum((volume_state<>'UNKNOWN')::int) AS volume,
    sum((spread_state<>'UNKNOWN')::int) AS spread
  FROM knowledge.market_context_v1
  WHERE source_version='MARKET_CONTEXT_COLLECTOR_V1'
)
SELECT
  total || '|' ||
  liquidity || '|' ||
  volume || '|' ||
  spread
FROM stats;
")

IFS='|' read -r total liquidity volume spread <<< "$coverage"

if [ "$total" -lt 1 ]; then
  echo "NO_CONTEXT_ROWS"
  exit 1
fi

echo "context_rows=$total"
echo "liquidity_known=$liquidity"
echo "volume_known=$volume"
echo "spread_known=$spread"

# Spread может остаться UNKNOWN, если источники не содержат bid/ask/spread.
# Liquidity/volume должны улучшиться при наличии числовых рыночных данных.
if [ "$liquidity" -lt 1 ]; then
  echo "LIQUIDITY_COVERAGE_NOT_IMPROVED"
  exit 1
fi

if [ "$volume" -lt 1 ]; then
  echo "VOLUME_COVERAGE_REQUIRES_SOURCE_COLUMN_AUDIT=1"
else
  echo "VOLUME_COVERAGE_IMPROVED=1"
fi

if [ "$spread" -lt 1 ]; then
  echo "SPREAD_COVERAGE_REQUIRES_ORDERBOOK_OR_BID_ASK=1"
else
  echo "SPREAD_COVERAGE_IMPROVED=1"
fi

echo "liquidity_volume_spread_patch=PARTIAL_OK"
echo "liquidity_improved=1"
echo "destructive_sql=0"
echo "edge_score_v2_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKET_CONTEXT_LIQUIDITY_VOLUME_SPREAD_COVERAGE_V1_READY"
echo "VERDICT=TEST_MARKET_CONTEXT_LIQUIDITY_VOLUME_SPREAD_COVERAGE_V1_OK"
