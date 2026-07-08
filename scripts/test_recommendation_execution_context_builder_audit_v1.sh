#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RECOMMENDATION_EXECUTION_CONTEXT_BUILDER_AUDIT_V1 ==="

mkdir -p reports
report="reports/recommendation_execution_context_builder_audit_v1.txt"

{
echo "======================================================"
echo "RECOMMENDATION EXECUTION CONTEXT BUILDER AUDIT V1"
echo "======================================================"
echo "generated_at=$(date -Is)"
echo

echo "=== TRADING PLAN SUMMARY ==="
psql -d finam_core -P pager=off -c "
SELECT
  source_version,
  count(*) AS rows_total,
  count(DISTINCT recommendation_id) AS recommendations,
  min(created_at) AS first_created_at,
  max(created_at) AS last_created_at
FROM knowledge.recommendation_execution_context_v1
GROUP BY source_version
ORDER BY rows_total DESC, source_version;
"

echo
echo "=== SAFETY FLAGS ==="
psql -d finam_core -P pager=off -c "
SELECT
  count(*) AS rows_total,
  sum((execution_allowed<>0)::int) AS execution_allowed_bad,
  sum((runtime_allowed<>0)::int) AS runtime_allowed_bad,
  sum((micro_live_allowed<>0)::int) AS micro_live_allowed_bad
FROM knowledge.recommendation_execution_context_v1;
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
WHERE r.recommendation_id IS NULL
   OR mc.context_id IS NULL
   OR ec.edge_context_id IS NULL
   OR d.direction_code IS NULL;
"

echo
echo "=== PLAN COMPLETENESS ==="
psql -d finam_core -P pager=off -c "
SELECT
  count(*) AS rows_total,
  sum((direction_code IS NOT NULL)::int) AS with_direction,
  sum((entry_price IS NOT NULL)::int) AS with_entry,
  sum((invalidation_price IS NOT NULL)::int) AS with_invalidation,
  sum((target_price IS NOT NULL)::int) AS with_target,
  sum((horizon_bars > 0)::int) AS with_horizon,
  sum((risk_unit > 0)::int) AS with_risk_unit
FROM knowledge.recommendation_execution_context_v1
WHERE source_version='RECOMMENDATION_EXECUTION_CONTEXT_MODELS_V1';
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
  execution_allowed,
  runtime_allowed,
  micro_live_allowed,
  created_at
FROM knowledge.recommendation_execution_context_v1
WHERE source_version='RECOMMENDATION_EXECUTION_CONTEXT_MODELS_V1'
ORDER BY created_at DESC
LIMIT 20;
"

echo
echo "=== BUILDER EVIDENCE ==="
psql -d finam_core -P pager=off -c "
SELECT
  execution_context_id,
  evidence_json
FROM knowledge.recommendation_execution_context_v1
WHERE source_version='RECOMMENDATION_EXECUTION_CONTEXT_MODELS_V1'
ORDER BY created_at DESC
LIMIT 20;
"

echo
echo "=== AUDIT DECISION ==="

rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.recommendation_execution_context_v1
WHERE source_version='RECOMMENDATION_EXECUTION_CONTEXT_MODELS_V1';
")

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.recommendation_execution_context_v1
WHERE execution_allowed<>0
   OR runtime_allowed<>0
   OR micro_live_allowed<>0;
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
WHERE r.recommendation_id IS NULL
   OR mc.context_id IS NULL
   OR ec.edge_context_id IS NULL
   OR d.direction_code IS NULL;
")

incomplete=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.recommendation_execution_context_v1
WHERE source_version='RECOMMENDATION_EXECUTION_CONTEXT_MODELS_V1'
  AND (
    direction_code IS NULL
    OR entry_price IS NULL
    OR invalidation_price IS NULL
    OR target_price IS NULL
    OR horizon_bars <= 0
    OR risk_unit <= 0
  );
")

echo "trading_plan_rows=${rows}"
echo "unsafe_rows=${unsafe}"
echo "bad_fk_rows=${bad_fk}"
echo "incomplete_rows=${incomplete}"

if [ "$rows" -lt 1 ]; then
  echo "TRADING_PLAN_ROWS_MISSING"
  exit 1
fi

if [ "$unsafe" != "0" ]; then
  echo "UNSAFE_TRADING_PLAN_ROWS=$unsafe"
  exit 1
fi

if [ "$bad_fk" != "0" ]; then
  echo "BAD_FK_ROWS=$bad_fk"
  exit 1
fi

if [ "$incomplete" != "0" ]; then
  echo "INCOMPLETE_TRADING_PLAN_ROWS=$incomplete"
  exit 1
fi

echo
echo "=== SAFETY ==="
echo "execution_allowed=0"
echo "runtime_allowed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo

echo "VERDICT=RECOMMENDATION_EXECUTION_CONTEXT_BUILDER_AUDIT_V1_READY"
} | tee "$report"

grep -q "VERDICT=RECOMMENDATION_EXECUTION_CONTEXT_BUILDER_AUDIT_V1_READY" "$report"

# Проверяем только реальные SQL-команды, а не строку grep внутри самого теста.
if grep -RInE '^[[:space:]]*(DROP[[:space:]]+TABLE|TRUNCATE|DELETE[[:space:]]+FROM|UPDATE[[:space:]]+runtime|UPDATE[[:space:]]+execution|INSERT[[:space:]]+INTO[[:space:]]+.*orders|INSERT[[:space:]]+INTO[[:space:]]+.*fills)' \
  scripts/test_recommendation_execution_context_builder_audit_v1.sh; then
  echo "DANGEROUS_CODE_FOUND"
  exit 1
fi

echo "report=$report"
echo "mode=read_only_audit"
echo "execution_allowed=0"
echo "runtime_allowed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=RECOMMENDATION_EXECUTION_CONTEXT_BUILDER_AUDIT_V1_READY"
echo "VERDICT=TEST_RECOMMENDATION_EXECUTION_CONTEXT_BUILDER_AUDIT_V1_OK"
