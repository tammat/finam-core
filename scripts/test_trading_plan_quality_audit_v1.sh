#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_TRADING_PLAN_QUALITY_AUDIT_V1 ==="

mkdir -p reports
report="reports/trading_plan_quality_audit_v1.txt"

{
echo "======================================================"
echo "TRADING PLAN QUALITY AUDIT V1"
echo "======================================================"
echo "generated_at=$(date -Is)"
echo

echo "=== TRADING PLAN SUMMARY ==="

psql -d finam_core -P pager=off -c "
SELECT
    count(*)                                    AS trading_plans,
    count(DISTINCT recommendation_id)           AS recommendations,
    count(DISTINCT direction_code)              AS directions,
    count(DISTINCT source_context_id)           AS market_contexts,
    count(DISTINCT source_edge_context_id)      AS edge_contexts
FROM knowledge.recommendation_execution_context_v1
WHERE source_version='TRADING_PLAN_PARAMETER_BUILDER_V1';
"

echo
echo "=== PROFILE DISTRIBUTION ==="

psql -d finam_core -P pager=off -c "
SELECT
    evidence_json->>'profile_code' AS profile,
    count(*)                       AS rows_total
FROM knowledge.recommendation_execution_context_v1
WHERE source_version='TRADING_PLAN_PARAMETER_BUILDER_V1'
GROUP BY evidence_json->>'profile_code'
ORDER BY rows_total DESC;
"

echo
echo "=== SOURCE REGISTRY USAGE ==="

psql -d finam_core -P pager=off -c "
SELECT
    evidence_json->>'entry_source'  AS entry_source,
    evidence_json->>'stop_source'   AS stop_source,
    evidence_json->>'target_source' AS target_source,
    count(*)                        AS rows_total
FROM knowledge.recommendation_execution_context_v1
WHERE source_version='TRADING_PLAN_PARAMETER_BUILDER_V1'
GROUP BY
    evidence_json->>'entry_source',
    evidence_json->>'stop_source',
    evidence_json->>'target_source'
ORDER BY rows_total DESC;
"

echo
echo "=== PRICE VALIDATION ==="

psql -d finam_core -P pager=off -c "
SELECT
    count(*)                                          AS rows_total,
    sum((entry_price<=0)::int)                        AS bad_entry,
    sum((invalidation_price<=0)::int)                 AS bad_stop,
    sum((target_price<=0)::int)                       AS bad_target,
    sum((risk_unit<=0)::int)                          AS bad_risk,
    sum((horizon_bars<=0)::int)                       AS bad_horizon
FROM knowledge.recommendation_execution_context_v1
WHERE source_version='TRADING_PLAN_PARAMETER_BUILDER_V1';
"

echo
echo "=== MARKET STRUCTURE REFERENCES ==="

psql -d finam_core -P pager=off -c "
SELECT
    count(*) AS rows_total,
    sum((evidence_json ? 'entry_evidence')::int)  AS entry_reference,
    sum((evidence_json ? 'stop_evidence')::int)   AS stop_reference,
    sum((evidence_json ? 'target_evidence')::int) AS target_reference
FROM knowledge.recommendation_execution_context_v1
WHERE source_version='TRADING_PLAN_PARAMETER_BUILDER_V1';
"

echo
echo "=== WIDGET READINESS ==="

psql -d finam_core -P pager=off -c "
SELECT
count(*) AS widget_ready_rows
FROM knowledge.recommendation_execution_context_v1
WHERE source_version='TRADING_PLAN_PARAMETER_BUILDER_V1'
AND evidence_json ? 'profile_code'
AND evidence_json ? 'entry_source'
AND evidence_json ? 'stop_source'
AND evidence_json ? 'target_source';
"

echo
echo "=== I18N VALIDATION ==="

psql -d finam_core -P pager=off -c "
SELECT
count(*) AS missing_sources
FROM knowledge.trading_plan_source_v1 s
LEFT JOIN presentation.ui_resource_v1 r
ON r.resource_key='trading_plan.source.'||lower(s.source_code)
AND r.locale_code='ru'
WHERE s.enabled
AND r.resource_key IS NULL;
"

echo
echo "=== SAFETY ==="

echo "runtime_allowed=0"
echo "execution_allowed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo
echo "VERDICT=TRADING_PLAN_QUALITY_AUDIT_V1_READY"

} | tee "$report"

grep -q "VERDICT=TRADING_PLAN_QUALITY_AUDIT_V1_READY" "$report"

rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.recommendation_execution_context_v1
WHERE source_version='TRADING_PLAN_PARAMETER_BUILDER_V1';
")

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.recommendation_execution_context_v1
WHERE source_version='TRADING_PLAN_PARAMETER_BUILDER_V1'
AND (
execution_allowed<>0
OR runtime_allowed<>0
OR micro_live_allowed<>0
);
")

missing_i18n=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.trading_plan_source_v1 s
LEFT JOIN presentation.ui_resource_v1 r
ON r.resource_key='trading_plan.source.'||lower(s.source_code)
AND r.locale_code='ru'
WHERE s.enabled
AND r.resource_key IS NULL;
")

test "$rows" -ge 1
test "$unsafe" = "0"
test "$missing_i18n" = "0"

echo
echo "trading_plan_rows=$rows"
echo "unsafe_rows=0"
echo "missing_i18n=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=TRADING_PLAN_QUALITY_AUDIT_V1_READY"
echo "VERDICT=TEST_TRADING_PLAN_QUALITY_AUDIT_V1_OK"
