#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_TRADING_PLAN_PARAMETER_BUILDER_AUDIT_V1 ==="

mkdir -p reports
report="reports/trading_plan_parameter_builder_audit_v1.txt"

{
echo "======================================================"
echo "TRADING PLAN PARAMETER BUILDER AUDIT V1"
echo "======================================================"
echo "generated_at=$(date -Is)"
echo

echo "=== TRADING PLAN PARAMETER SUMMARY ==="
psql -d finam_core -P pager=off -c "
SELECT
  count(*) AS rows_total,
  count(DISTINCT recommendation_id) AS recommendations,
  count(DISTINCT direction_code) AS directions,
  min(created_at) AS first_created_at,
  max(created_at) AS last_created_at
FROM knowledge.recommendation_execution_context_v1
WHERE source_version='TRADING_PLAN_PARAMETER_BUILDER_V1';
"

echo
echo "=== PROFILE / SOURCE USAGE ==="
psql -d finam_core -P pager=off -c "
SELECT
  evidence_json->>'profile_code' AS profile_code,
  evidence_json->>'entry_source' AS entry_source,
  evidence_json->>'stop_source' AS stop_source,
  evidence_json->>'target_source' AS target_source,
  count(*) AS rows_total
FROM knowledge.recommendation_execution_context_v1
WHERE source_version='TRADING_PLAN_PARAMETER_BUILDER_V1'
GROUP BY
  evidence_json->>'profile_code',
  evidence_json->>'entry_source',
  evidence_json->>'stop_source',
  evidence_json->>'target_source'
ORDER BY rows_total DESC;
"

echo
echo "=== PRICE QUALITY ==="
psql -d finam_core -P pager=off -c "
SELECT
  count(*) AS rows_total,
  sum((entry_price IS NULL)::int) AS missing_entry,
  sum((invalidation_price IS NULL)::int) AS missing_stop,
  sum((target_price IS NULL)::int) AS missing_target,
  sum((risk_unit IS NULL OR risk_unit <= 0)::int) AS invalid_risk_unit,
  sum((horizon_bars IS NULL OR horizon_bars <= 0)::int) AS invalid_horizon,
  sum((entry_price=1 AND invalidation_price=1 AND target_price=1)::int) AS skeleton_price_rows
FROM knowledge.recommendation_execution_context_v1
WHERE source_version='TRADING_PLAN_PARAMETER_BUILDER_V1';
"

echo
echo "=== EVIDENCE QUALITY ==="
psql -d finam_core -P pager=off -c "
SELECT
  count(*) AS rows_total,
  sum((NOT evidence_json ? 'profile_code')::int) AS missing_profile_code,
  sum((NOT evidence_json ? 'entry_evidence')::int) AS missing_entry_evidence,
  sum((NOT evidence_json ? 'stop_evidence')::int) AS missing_stop_evidence,
  sum((NOT evidence_json ? 'target_evidence')::int) AS missing_target_evidence,
  sum((NOT evidence_json ? 'execution_allowed')::int) AS missing_execution_flag,
  sum((NOT evidence_json ? 'runtime_allowed')::int) AS missing_runtime_flag,
  sum((NOT evidence_json ? 'micro_live_allowed')::int) AS missing_micro_live_flag
FROM knowledge.recommendation_execution_context_v1
WHERE source_version='TRADING_PLAN_PARAMETER_BUILDER_V1';
"

echo
echo "=== FK INTEGRITY ==="
psql -d finam_core -P pager=off -c "
SELECT
  count(*) AS bad_fk_rows
FROM knowledge.recommendation_execution_context_v1 x
LEFT JOIN knowledge.recommendation_result_v1 r
  ON r.recommendation_id=x.recommendation_id
LEFT JOIN knowledge.market_context_v1 mc
  ON mc.context_id=x.source_context_id
LEFT JOIN knowledge.edge_context_v1 ec
  ON ec.edge_context_id=x.source_edge_context_id
LEFT JOIN knowledge.recommendation_direction_v1 d
  ON d.direction_code=x.direction_code
WHERE x.source_version='TRADING_PLAN_PARAMETER_BUILDER_V1'
  AND (
       r.recommendation_id IS NULL
    OR mc.context_id IS NULL
    OR ec.edge_context_id IS NULL
    OR d.direction_code IS NULL
  );
"

echo
echo "=== SAFETY FLAGS ==="
psql -d finam_core -P pager=off -c "
SELECT
  count(*) AS rows_total,
  sum((execution_allowed<>0)::int) AS execution_allowed_bad,
  sum((runtime_allowed<>0)::int) AS runtime_allowed_bad,
  sum((micro_live_allowed<>0)::int) AS micro_live_allowed_bad
FROM knowledge.recommendation_execution_context_v1
WHERE source_version='TRADING_PLAN_PARAMETER_BUILDER_V1';
"

echo
echo "=== LATEST TRADING PLANS ==="
psql -d finam_core -P pager=off -c "
SELECT
  execution_context_id,
  recommendation_id,
  direction_code,
  entry_price,
  invalidation_price,
  target_price,
  horizon_bars,
  risk_unit,
  created_at
FROM knowledge.recommendation_execution_context_v1
WHERE source_version='TRADING_PLAN_PARAMETER_BUILDER_V1'
ORDER BY created_at DESC
LIMIT 20;
"

echo
echo "=== AUDIT DECISION ==="

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

bad_fk=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.recommendation_execution_context_v1 x
LEFT JOIN knowledge.recommendation_result_v1 r
  ON r.recommendation_id=x.recommendation_id
LEFT JOIN knowledge.market_context_v1 mc
  ON mc.context_id=x.source_context_id
LEFT JOIN knowledge.edge_context_v1 ec
  ON ec.edge_context_id=x.source_edge_context_id
LEFT JOIN knowledge.recommendation_direction_v1 d
  ON d.direction_code=x.direction_code
WHERE x.source_version='TRADING_PLAN_PARAMETER_BUILDER_V1'
  AND (
       r.recommendation_id IS NULL
    OR mc.context_id IS NULL
    OR ec.edge_context_id IS NULL
    OR d.direction_code IS NULL
  );
")

bad_quality=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.recommendation_execution_context_v1
WHERE source_version='TRADING_PLAN_PARAMETER_BUILDER_V1'
  AND (
       entry_price IS NULL
    OR invalidation_price IS NULL
    OR target_price IS NULL
    OR risk_unit IS NULL
    OR risk_unit <= 0
    OR horizon_bars IS NULL
    OR horizon_bars <= 0
    OR (entry_price=1 AND invalidation_price=1 AND target_price=1)
    OR NOT evidence_json ? 'profile_code'
    OR NOT evidence_json ? 'entry_evidence'
    OR NOT evidence_json ? 'stop_evidence'
    OR NOT evidence_json ? 'target_evidence'
  );
")

echo "trading_plan_parameter_rows=${rows}"
echo "unsafe_rows=${unsafe}"
echo "bad_fk_rows=${bad_fk}"
echo "bad_quality_rows=${bad_quality}"

if [ "$rows" -lt 1 ]; then
  echo "TRADING_PLAN_PARAMETER_ROWS_MISSING"
  exit 1
fi

if [ "$unsafe" != "0" ]; then
  echo "UNSAFE_ROWS=$unsafe"
  exit 1
fi

if [ "$bad_fk" != "0" ]; then
  echo "BAD_FK_ROWS=$bad_fk"
  exit 1
fi

if [ "$bad_quality" != "0" ]; then
  echo "BAD_QUALITY_ROWS=$bad_quality"
  exit 1
fi

echo
echo "=== SAFETY ==="
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo

echo "VERDICT=TRADING_PLAN_PARAMETER_BUILDER_AUDIT_V1_READY"
} | tee "$report"

grep -q "VERDICT=TRADING_PLAN_PARAMETER_BUILDER_AUDIT_V1_READY" "$report"

echo "report=$report"
echo "mode=read_only_audit"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TRADING_PLAN_PARAMETER_BUILDER_AUDIT_V1_READY"
echo "VERDICT=TEST_TRADING_PLAN_PARAMETER_BUILDER_AUDIT_V1_OK"
