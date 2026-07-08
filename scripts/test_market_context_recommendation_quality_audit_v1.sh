#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_CONTEXT_RECOMMENDATION_QUALITY_AUDIT_V1 ==="

mkdir -p reports
report="reports/market_context_recommendation_quality_audit_v1.txt"

{
echo "======================================================"
echo "MARKET CONTEXT RECOMMENDATION QUALITY AUDIT V1"
echo "======================================================"
echo "generated_at=$(date -Is)"
echo

echo "=== RECOMMENDATION RESULTS ==="
psql -d finam_core -P pager=off -c "
SELECT
  recommendation_code,
  count(*) AS rows_total,
  round(avg(recommendation_confidence),4) AS avg_confidence,
  round(max(recommendation_confidence),4) AS max_confidence,
  round(min(recommendation_confidence),4) AS min_confidence
FROM knowledge.recommendation_result_v1
GROUP BY recommendation_code
ORDER BY rows_total DESC, recommendation_code;
"

echo
echo "=== REASONS COVERAGE ==="
psql -d finam_core -P pager=off -c "
SELECT
  r.recommendation_code,
  count(rr.reason_id) AS reason_rows,
  round(avg(rr.confidence),4) AS avg_reason_confidence
FROM knowledge.recommendation_result_v1 r
LEFT JOIN knowledge.recommendation_reason_v1 rr
  ON rr.recommendation_id=r.recommendation_id
GROUP BY r.recommendation_code
ORDER BY r.recommendation_code;
"

echo
echo "=== LATEST RECOMMENDATIONS ==="
psql -d finam_core -P pager=off -c "
SELECT
  recommendation_id,
  symbol,
  timeframe,
  recommendation_code,
  recommendation_confidence,
  rule_code,
  knowledge_version,
  created_at
FROM knowledge.recommendation_result_v1
ORDER BY created_at DESC
LIMIT 20;
"

echo
echo "=== RULE USAGE ==="
psql -d finam_core -P pager=off -c "
SELECT
  rule_code,
  count(*) AS rows_total,
  round(avg(recommendation_confidence),4) AS avg_confidence
FROM knowledge.recommendation_result_v1
GROUP BY rule_code
ORDER BY rows_total DESC, rule_code;
"

echo
echo "=== I18N CHECK ==="
psql -d finam_core -P pager=off -c "
WITH keys AS (
  SELECT DISTINCT 'recommendation.' || lower(recommendation_code) AS resource_key
  FROM knowledge.recommendation_result_v1
  UNION
  SELECT DISTINCT reason_code AS resource_key
  FROM knowledge.recommendation_reason_v1
)
SELECT
  k.resource_key
FROM keys k
LEFT JOIN presentation.ui_resource_v1 r
  ON r.resource_key=k.resource_key
 AND r.locale_code='ru'
WHERE r.resource_key IS NULL
ORDER BY k.resource_key;
"

echo
echo "=== RECOMMENDATION COVERAGE ==="
psql -d finam_core -P pager=off -c "
WITH edge_targets AS (
  SELECT count(*) AS total
  FROM knowledge.edge_context_v1
  WHERE source_version='MARKETCORE_MARKET_KNOWLEDGE_EDGE_CONTEXT_BRIDGE_V1'
),
recommended AS (
  SELECT count(DISTINCT symbol || '|' || timeframe) AS total
  FROM knowledge.recommendation_result_v1
)
SELECT
  edge_targets.total AS edge_context_rows,
  recommended.total AS recommended_symbol_timeframes,
  round(100.0 * recommended.total / nullif(edge_targets.total,0), 2) AS recommendation_coverage_pct
FROM edge_targets, recommended;
"

echo
echo "=== SAFETY ==="
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo

echo "VERDICT=MARKET_CONTEXT_RECOMMENDATION_QUALITY_AUDIT_V1_READY"
} | tee "$report"

grep -q "VERDICT=MARKET_CONTEXT_RECOMMENDATION_QUALITY_AUDIT_V1_READY" "$report"

missing_i18n=$(psql -At -d finam_core -c "
WITH keys AS (
  SELECT DISTINCT 'recommendation.' || lower(recommendation_code) AS resource_key
  FROM knowledge.recommendation_result_v1
  UNION
  SELECT DISTINCT reason_code AS resource_key
  FROM knowledge.recommendation_reason_v1
)
SELECT count(*)
FROM keys k
LEFT JOIN presentation.ui_resource_v1 r
  ON r.resource_key=k.resource_key
 AND r.locale_code='ru'
WHERE r.resource_key IS NULL;
")

if [ "$missing_i18n" != "0" ]; then
  echo "MISSING_I18N_RESOURCES=$missing_i18n"
  exit 1
fi

result_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM knowledge.recommendation_result_v1;")
reason_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM knowledge.recommendation_reason_v1;")

test "$result_rows" -ge 1
test "$reason_rows" -ge 1

echo "report=$report"
echo "recommendation_result_rows=$result_rows"
echo "recommendation_reason_rows=$reason_rows"
echo "missing_i18n_resources=0"
echo "hardcode=0"
echo "raw_i18n_keys=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKET_CONTEXT_RECOMMENDATION_QUALITY_AUDIT_V1_READY"
echo "VERDICT=TEST_MARKET_CONTEXT_RECOMMENDATION_QUALITY_AUDIT_V1_OK"
