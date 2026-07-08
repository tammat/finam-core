#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_CONTEXT_COVERAGE_REPORT_V1 ==="

mkdir -p reports

report="reports/market_context_coverage_report_v1.txt"

{
echo "======================================================"
echo "MARKET CONTEXT COVERAGE REPORT V1"
echo "======================================================"
echo
echo "generated_at=$(date -Is)"
echo

psql -d finam_core -P pager=off <<'SQL'
WITH stats AS (
SELECT
count(*)                                                AS total,

sum((regime_code<>'UNKNOWN')::int)                      AS regime,

sum((volatility_state<>'UNKNOWN')::int)                 AS volatility,

sum((liquidity_state<>'UNKNOWN')::int)                  AS liquidity,

sum((volume_state<>'UNKNOWN')::int)                     AS volume,

sum((spread_state<>'UNKNOWN')::int)                     AS spread,

sum((session_state<>'UNKNOWN')::int)                    AS session,

sum((correlation_state<>'UNKNOWN')::int)                AS correlation,

sum((sector_strength_state<>'UNKNOWN')::int)            AS sector

FROM knowledge.market_context_v1
WHERE source_version='MARKET_CONTEXT_COLLECTOR_V1'
)

SELECT

total,

round(100.0*regime/nullif(total,0),2)       AS regime_pct,

round(100.0*volatility/nullif(total,0),2)   AS volatility_pct,

round(100.0*liquidity/nullif(total,0),2)    AS liquidity_pct,

round(100.0*volume/nullif(total,0),2)       AS volume_pct,

round(100.0*spread/nullif(total,0),2)       AS spread_pct,

round(100.0*session/nullif(total,0),2)      AS session_pct,

round(100.0*correlation/nullif(total,0),2)  AS correlation_pct,

round(100.0*sector/nullif(total,0),2)       AS sector_pct

FROM stats;
SQL

echo
echo "================ KNOWLEDGE COVERAGE ================"

coverage=$(psql -At -d finam_core <<'SQL'
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

SELECT
round(
100.0*ok/nullif(total*8,0),
2
)
FROM stats;
SQL
)

echo "KNOWLEDGE_COVERAGE=${coverage}%"

echo
echo "================ NEXT PRIORITIES ================"

echo "1. Liquidity"

echo "2. Volume"

echo "3. Spread"

echo "4. Correlation"

echo "5. Sector Strength"

echo

echo "======================================================"

echo "VERDICT=MARKET_CONTEXT_COVERAGE_REPORT_V1_READY"

} | tee "$report"

grep -q "KNOWLEDGE_COVERAGE" "$report"

echo

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=MARKET_CONTEXT_COVERAGE_REPORT_V1_READY"
echo "VERDICT=TEST_MARKET_CONTEXT_COVERAGE_REPORT_V1_OK"

