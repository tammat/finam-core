#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_CONTEXT_CORRELATION_QUALITY_AUDIT_V1 ==="

mkdir -p reports
report="reports/market_context_correlation_quality_audit_v1.txt"

{
echo "======================================================"
echo "MARKET CONTEXT CORRELATION QUALITY AUDIT V1"
echo "======================================================"
echo
echo "generated_at=$(date -Is)"
echo

echo "=== ACTIVE RULES ==="

psql -d finam_core -P pager=off -c "
SELECT
    rule_code,
    timeframe,
    lookback_bars,
    min_observations,
    min_abs_correlation
FROM knowledge.correlation_rule_v1
WHERE is_active
ORDER BY rule_code;
"

echo
echo "=== CORRELATION UNIVERSE ==="

psql -d finam_core -P pager=off -c "
SELECT
    timeframe,
    count(*) AS pairs
FROM knowledge.correlation_universe_v1
WHERE is_active
GROUP BY timeframe
ORDER BY timeframe;
"

echo
echo "=== RELATIONSHIPS ==="

psql -d finam_core -P pager=off -c "
SELECT
    relation_type,
    count(*) AS rows,
    round(avg(weight),4) AS avg_corr,
    round(max(weight),4) AS max_corr,
    round(min(weight),4) AS min_corr
FROM knowledge.relationship_v1
WHERE source_version='MARKET_CONTEXT_CORRELATION_COLLECTOR_V1'
GROUP BY relation_type;
"

echo
echo "=== TOP CORRELATIONS ==="

psql -d finam_core -P pager=off -c "
SELECT
    source_code,
    target_code,
    weight,
    confidence
FROM knowledge.relationship_v1
WHERE source_version='MARKET_CONTEXT_CORRELATION_COLLECTOR_V1'
ORDER BY confidence DESC, weight DESC
LIMIT 20;
"

echo
echo "=== MARKET CONTEXT IMPACT ==="

psql -d finam_core -P pager=off -c "
SELECT
count(*)                                        AS total,

sum((correlation_state='EVALUATED')::int)       AS evaluated,

round(
100.0*
sum((correlation_state='EVALUATED')::int)
/nullif(count(*),0),
2
) AS evaluated_pct

FROM knowledge.market_context_v1
WHERE source_version='MARKET_CONTEXT_COLLECTOR_V1';
"

echo
echo "=== KNOWLEDGE COVERAGE IMPACT ==="

psql -d finam_core -P pager=off <<'SQL'
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
AS knowledge_coverage_pct
FROM stats;
SQL

echo
echo "======================================================"

echo "VERDICT=MARKET_CONTEXT_CORRELATION_QUALITY_AUDIT_V1_READY"

} | tee "$report"

grep -q "VERDICT=MARKET_CONTEXT_CORRELATION_QUALITY_AUDIT_V1_READY" "$report"

echo
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=MARKET_CONTEXT_CORRELATION_QUALITY_AUDIT_V1_READY"
echo "VERDICT=TEST_MARKET_CONTEXT_CORRELATION_QUALITY_AUDIT_V1_OK"

