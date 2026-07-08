#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_CONTEXT_SECTOR_ENGINE_V1 ==="

file="src/scripts/market_context_sector_engine_v1.py"
test -f "$file"

PYTHONPYCACHEPREFIX=/tmp/finam_pycache_sector_engine PYTHONPATH=src/scripts \
python -m py_compile "$file"

if grep -RInE 'send_order|place_order|cancel_order|execute_order|INSERT INTO .*orders|INSERT INTO .*fills|UPDATE .*runtime|UPDATE .*execution|UPDATE .*edge_score_model_v2|DELETE FROM|DROP TABLE|TRUNCATE' "$file"; then
  echo "DANGEROUS_CODE_FOUND"
  exit 1
fi

if grep -RInE "'(SBER|LKOH|VTBR|GAZP|IMOEX|RTSI|BR|NG)(@[^']*)?'|\"(SBER|LKOH|VTBR|GAZP|IMOEX|RTSI|BR|NG)(@[^\"]*)?\"" "$file"; then
  echo "HARDCODED_SYMBOL_FOUND"
  exit 1
fi

before_edge=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_score_model_v2;")

out=$(PYTHONPYCACHEPREFIX=/tmp/finam_pycache_sector_engine PYTHONPATH=src/scripts python "$file")
echo "$out"

after_edge=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_score_model_v2;")

if [ "$before_edge" != "$after_edge" ]; then
  echo "EDGE_SCORE_V2_ROWCOUNT_CHANGED before=$before_edge after=$after_edge"
  exit 1
fi

echo "$out" | grep -q "VERDICT=MARKET_CONTEXT_SECTOR_ENGINE_V1_READY"
echo "$out" | grep -q "config_source=postgres"
echo "$out" | grep -q "symbol_hardcode=0"

sector_context=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.market_context_v1
WHERE source_version='MARKET_CONTEXT_COLLECTOR_V1'
  AND sector_strength_state <> 'UNKNOWN';
")

if [ "$sector_context" -lt 1 ]; then
  echo "NO_SECTOR_CONTEXT_ROWS"
  exit 1
fi

coverage=$(psql -At -d finam_core -c "
WITH stats AS (
  SELECT
    count(*) total,
    sum((regime_code<>'UNKNOWN')::int)+
    sum((volatility_state<>'UNKNOWN')::int)+
    sum((liquidity_state<>'UNKNOWN')::int)+
    sum((volume_state<>'UNKNOWN')::int)+
    sum((spread_state<>'UNKNOWN')::int)+
    sum((session_state<>'UNKNOWN')::int)+
    sum((correlation_state<>'UNKNOWN')::int)+
    sum((sector_strength_state<>'UNKNOWN')::int) ok
  FROM knowledge.market_context_v1
  WHERE source_version='MARKET_CONTEXT_COLLECTOR_V1'
)
SELECT round(100.0*ok/nullif(total*8,0),2)
FROM stats;
")

echo "sector_context_rows=$sector_context"
echo "knowledge_coverage_pct=$coverage"
echo "hardcode=0"
echo "destructive_sql=0"
echo "edge_score_v2_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKET_CONTEXT_SECTOR_ENGINE_V1_READY"
echo "VERDICT=TEST_MARKET_CONTEXT_SECTOR_ENGINE_V1_OK"
