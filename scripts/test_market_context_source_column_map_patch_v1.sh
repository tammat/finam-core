#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_CONTEXT_SOURCE_COLUMN_MAP_PATCH_V1 ==="

files=(
  src/scripts/market_context_column_map_v1.py
  src/scripts/market_context_collector_v1.py
)

for f in "${files[@]}"; do
  test -f "$f"
  PYTHONPYCACHEPREFIX=/tmp/finam_pycache_context_column_map PYTHONPATH=src/scripts python -m py_compile "$f"
done

if grep -RInE 'send_order|place_order|cancel_order|execute_order|INSERT INTO .*orders|INSERT INTO .*fills|UPDATE .*runtime|UPDATE .*execution|UPDATE .*edge_score_model_v2|DELETE FROM|DROP TABLE|TRUNCATE' "${files[@]}"; then
  echo "DANGEROUS_CODE_FOUND"
  exit 1
fi

PYTHONPATH=src/scripts python - <<'PY'
from market_context_column_map_v1 import read_mapped_value

row = {
    "atr_state": "high",
    "volume_quality": "normal",
    "spread_quality": "tight",
    "event_type": "main_session",
}
assert read_mapped_value(row, "volatility") == "HIGH"
assert read_mapped_value(row, "liquidity") == "NORMAL"
assert read_mapped_value(row, "volume") == "NORMAL"
assert read_mapped_value(row, "spread") == "TIGHT"
assert read_mapped_value(row, "session") == "MAIN_SESSION"
assert read_mapped_value(row, "missing") == "UNKNOWN"

print("column_map=OK")
PY

before_edge=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_score_model_v2;")

out=$(PYTHONPYCACHEPREFIX=/tmp/finam_pycache_context_column_map PYTHONPATH=src/scripts python src/scripts/market_context_collector_v1.py)
echo "$out"

after_edge=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_score_model_v2;")

if [ "$before_edge" != "$after_edge" ]; then
  echo "EDGE_SCORE_V2_ROWCOUNT_CHANGED before=$before_edge after=$after_edge"
  exit 1
fi

echo "$out" | grep -q "VERDICT=MARKET_CONTEXT_COLLECTOR_V1_READY"

context_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.market_context_v1
WHERE source_version='MARKET_CONTEXT_COLLECTOR_V1';
")

known_core=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.market_context_v1
WHERE source_version='MARKET_CONTEXT_COLLECTOR_V1'
  AND regime_code <> 'UNKNOWN'
  AND volatility_state <> 'UNKNOWN'
  AND session_state <> 'UNKNOWN';
")

if [ "$context_rows" -lt 1 ]; then
  echo "NO_CONTEXT_ROWS"
  exit 1
fi

if [ "$known_core" -lt 1 ]; then
  echo "NO_CORE_CONTEXT_KNOWN_ROWS"
  exit 1
fi

echo "context_rows=$context_rows"
echo "known_core_context_rows=$known_core"
echo "column_map_patch=OK"
echo "destructive_sql=0"
echo "edge_score_v2_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKET_CONTEXT_SOURCE_COLUMN_MAP_PATCH_V1_READY"
echo "VERDICT=TEST_MARKET_CONTEXT_SOURCE_COLUMN_MAP_PATCH_V1_OK"
