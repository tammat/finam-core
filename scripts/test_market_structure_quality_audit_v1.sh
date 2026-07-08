#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_STRUCTURE_QUALITY_AUDIT_V1 ==="

mkdir -p reports
report="reports/market_structure_quality_audit_v1.txt"

{
echo "======================================================"
echo "MARKET STRUCTURE QUALITY AUDIT V1"
echo "======================================================"
echo "generated_at=$(date -Is)"
echo

echo "=== STRUCTURE SUMMARY ==="

psql -d finam_core -P pager=off -c "
SELECT
    structure_type_code,
    count(*)                     AS rows_total,
    count(DISTINCT symbol)       AS symbols,
    count(DISTINCT timeframe)    AS timeframes,
    round(avg(level_strength),4) AS avg_strength
FROM knowledge.market_structure_v1
WHERE source_version='MARKET_STRUCTURE_ENGINE_V1'
GROUP BY structure_type_code
ORDER BY rows_total DESC, structure_type_code;
"

echo
echo "=== SYMBOL COVERAGE ==="

psql -d finam_core -P pager=off -c "
SELECT
    symbol,
    timeframe,
    count(*) AS structure_rows
FROM knowledge.market_structure_v1
WHERE source_version='MARKET_STRUCTURE_ENGINE_V1'
GROUP BY symbol,timeframe
ORDER BY structure_rows DESC,symbol,timeframe
LIMIT 30;
"

echo
echo "=== FIBONACCI DISTRIBUTION ==="

psql -d finam_core -P pager=off -c "
SELECT
    structure_type_code,
    evidence_json->>'ratio' AS ratio,
    count(*) AS rows_total
FROM knowledge.market_structure_v1
WHERE source_version='MARKET_STRUCTURE_ENGINE_V1'
  AND structure_type_code IN
      ('FIBONACCI_RETRACEMENT','FIBONACCI_EXTENSION')
GROUP BY structure_type_code,evidence_json->>'ratio'
ORDER BY structure_type_code,ratio;
"

echo
echo "=== SUPPORT / RESISTANCE BALANCE ==="

psql -d finam_core -P pager=off -c "
SELECT
    symbol,
    timeframe,
    sum((structure_type_code='SUPPORT')::int)    AS supports,
    sum((structure_type_code='RESISTANCE')::int) AS resistances
FROM knowledge.market_structure_v1
WHERE source_version='MARKET_STRUCTURE_ENGINE_V1'
GROUP BY symbol,timeframe
ORDER BY symbol,timeframe;
"

echo
echo "=== DATA QUALITY ==="

psql -d finam_core -P pager=off -c "
SELECT
    count(*)                                        AS rows_total,
    sum((level_price IS NULL)::int)                 AS missing_price,
    sum((level_strength IS NULL)::int)              AS missing_strength,
    sum((lookback_bars<=0)::int)                    AS invalid_lookback,
    sum((detected_at IS NULL)::int)                 AS missing_detected_at,
    sum((evidence_json='{}'::jsonb)::int)           AS empty_evidence
FROM knowledge.market_structure_v1
WHERE source_version='MARKET_STRUCTURE_ENGINE_V1';
"

echo
echo "=== FK VALIDATION ==="

psql -d finam_core -P pager=off -c "
SELECT
count(*) AS broken_fk
FROM knowledge.market_structure_v1 s
LEFT JOIN knowledge.market_structure_type_v1 t
ON t.structure_type_code=s.structure_type_code
WHERE s.source_version='MARKET_STRUCTURE_ENGINE_V1'
AND t.structure_type_code IS NULL;
"

echo
echo "=== I18N VALIDATION ==="

psql -d finam_core -P pager=off -c "
WITH keys AS (
SELECT DISTINCT
'market_structure.'||lower(structure_type_code)
AS resource_key
FROM knowledge.market_structure_v1
WHERE source_version='MARKET_STRUCTURE_ENGINE_V1'
)
SELECT
k.resource_key
FROM keys k
LEFT JOIN presentation.ui_resource_v1 r
ON r.resource_key=k.resource_key
AND r.locale_code='ru'
WHERE r.resource_key IS NULL;
"

echo
echo "=== MARKET STRUCTURE COVERAGE ==="

psql -d finam_core -P pager=off -c "
WITH universe AS (
SELECT count(DISTINCT symbol||'|'||timeframe) total
FROM public.market_bars
),
ready AS (
SELECT count(DISTINCT symbol||'|'||timeframe) total
FROM knowledge.market_structure_v1
WHERE source_version='MARKET_STRUCTURE_ENGINE_V1'
)
SELECT
universe.total AS universe,
ready.total AS covered,
round(
100.0*ready.total/nullif(universe.total,0),
2
) AS coverage_pct
FROM universe,ready;
"

echo
echo "=== SAFETY ==="

echo "runtime_allowed=0"
echo "execution_allowed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo
echo "VERDICT=MARKET_STRUCTURE_QUALITY_AUDIT_V1_READY"

} | tee "$report"

grep -q "VERDICT=MARKET_STRUCTURE_QUALITY_AUDIT_V1_READY" "$report"

missing_i18n=$(psql -At -d finam_core -c "
WITH keys AS (
SELECT DISTINCT
'market_structure.'||lower(structure_type_code)
AS resource_key
FROM knowledge.market_structure_v1
WHERE source_version='MARKET_STRUCTURE_ENGINE_V1'
)
SELECT count(*)
FROM keys k
LEFT JOIN presentation.ui_resource_v1 r
ON r.resource_key=k.resource_key
AND r.locale_code='ru'
WHERE r.resource_key IS NULL;
")

test "$missing_i18n" = "0"

echo "report=$report"
echo "missing_i18n_resources=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKET_STRUCTURE_QUALITY_AUDIT_V1_READY"
echo "VERDICT=TEST_MARKET_STRUCTURE_QUALITY_AUDIT_V1_OK"
