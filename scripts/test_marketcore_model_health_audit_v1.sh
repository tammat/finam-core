#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_MODEL_HEALTH_AUDIT_V1 ==="

mkdir -p reports
report="reports/marketcore_model_health_audit_v1.txt"

snapshot_id=$(psql -At -d finam_core -c "
SELECT model_health_snapshot_id
FROM analytics.marketcore_model_health_snapshot_v1
WHERE source_version='MARKETCORE_MODEL_HEALTH_ENGINE_V1'
ORDER BY created_at DESC
LIMIT 1;
")

test -n "$snapshot_id"

{
echo "======================================================"
echo "MARKETCORE MODEL HEALTH AUDIT V1"
echo "======================================================"
echo "generated_at=$(date -Is)"
echo "model_health_snapshot_id=${snapshot_id}"
echo

echo "=== SNAPSHOT ==="
psql -d finam_core -P pager=off -c "
SELECT *
FROM analytics.marketcore_model_health_snapshot_v1
WHERE model_health_snapshot_id=${snapshot_id};
"

echo
echo "=== COMPONENTS ==="
psql -d finam_core -P pager=off -c "
SELECT
  component_code,
  component_group,
  round(component_value,4) AS component_value,
  component_status,
  created_at
FROM analytics.marketcore_model_health_component_v1
WHERE model_health_snapshot_id=${snapshot_id}
ORDER BY component_code;
"

echo
echo "=== GATES ==="
psql -d finam_core -P pager=off -c "
SELECT
  gate_code,
  gate_status,
  gate_reason,
  created_at
FROM analytics.marketcore_model_health_gate_v1
WHERE model_health_snapshot_id=${snapshot_id}
ORDER BY gate_code;
"

echo
echo "=== RECOMMENDATIONS ==="
psql -d finam_core -P pager=off -c "
SELECT
  recommendation_code,
  recommendation_scope,
  recommendation_reason,
  recommended_action,
  approved,
  applied,
  auto_decision,
  created_at
FROM analytics.marketcore_model_health_recommendation_v1
WHERE model_health_snapshot_id=${snapshot_id}
ORDER BY created_at DESC, model_recommendation_id DESC;
"

echo
echo "=== FK / COMPLETENESS ==="
psql -d finam_core -P pager=off -c "
WITH checks AS (
  SELECT 'components' AS object_name, count(*) AS rows_total
  FROM analytics.marketcore_model_health_component_v1
  WHERE model_health_snapshot_id=${snapshot_id}
  UNION ALL
  SELECT 'gates', count(*)
  FROM analytics.marketcore_model_health_gate_v1
  WHERE model_health_snapshot_id=${snapshot_id}
  UNION ALL
  SELECT 'recommendations', count(*)
  FROM analytics.marketcore_model_health_recommendation_v1
  WHERE model_health_snapshot_id=${snapshot_id}
)
SELECT *
FROM checks
ORDER BY object_name;
"

echo
echo "=== I18N VALIDATION ==="
psql -d finam_core -P pager=off -c "
WITH keys AS (
  SELECT 'model.health.component.'||lower(component_code) AS resource_key
  FROM analytics.marketcore_model_health_component_v1
  WHERE model_health_snapshot_id=${snapshot_id}
  UNION ALL
  SELECT 'model.health.gate.'||lower(gate_status) AS resource_key
  FROM analytics.marketcore_model_health_gate_v1
  WHERE model_health_snapshot_id=${snapshot_id}
  UNION ALL
  SELECT 'model.health.recommendation.'||lower(recommendation_code) AS resource_key
  FROM analytics.marketcore_model_health_recommendation_v1
  WHERE model_health_snapshot_id=${snapshot_id}
  UNION ALL
  SELECT 'model.health.reason.'||lower(recommendation_reason) AS resource_key
  FROM analytics.marketcore_model_health_recommendation_v1
  WHERE model_health_snapshot_id=${snapshot_id}
  UNION ALL
  SELECT 'model.health.action.'||lower(recommended_action) AS resource_key
  FROM analytics.marketcore_model_health_recommendation_v1
  WHERE model_health_snapshot_id=${snapshot_id}
)
SELECT
  count(*) AS missing_i18n_resources
FROM keys k
LEFT JOIN presentation.ui_resource_v1 r
  ON r.resource_key=k.resource_key
 AND r.locale_code='ru'
WHERE r.resource_key IS NULL;
"

echo
echo "=== SAFETY FLAGS ==="
psql -d finam_core -P pager=off -c "
SELECT
  count(*) AS rows_total,
  sum((approved<>0)::int) AS approved_bad,
  sum((applied<>0)::int) AS applied_bad,
  sum((auto_decision<>0)::int) AS auto_decision_bad
FROM analytics.marketcore_model_health_recommendation_v1
WHERE model_health_snapshot_id=${snapshot_id};
"

echo
echo "=== AUDIT DECISION ==="

components=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.marketcore_model_health_component_v1
WHERE model_health_snapshot_id=${snapshot_id}
  AND source_version='MARKETCORE_MODEL_HEALTH_ENGINE_V1';
")

gates=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.marketcore_model_health_gate_v1
WHERE model_health_snapshot_id=${snapshot_id}
  AND source_version='MARKETCORE_MODEL_HEALTH_ENGINE_V1';
")

recommendations=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.marketcore_model_health_recommendation_v1
WHERE model_health_snapshot_id=${snapshot_id}
  AND source_version='MARKETCORE_MODEL_HEALTH_ENGINE_V1';
")

bad_status=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.marketcore_model_health_component_v1
WHERE model_health_snapshot_id=${snapshot_id}
  AND component_status NOT IN ('PASS','WARNING','BLOCKED');
")

bad_gate=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.marketcore_model_health_gate_v1
WHERE model_health_snapshot_id=${snapshot_id}
  AND gate_status NOT IN ('PASS','WARNING','BLOCKED','LOCKED');
")

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.marketcore_model_health_recommendation_v1
WHERE model_health_snapshot_id=${snapshot_id}
  AND (
       approved<>0
    OR applied<>0
    OR auto_decision<>0
  );
")

missing_i18n=$(psql -At -d finam_core -c "
WITH keys AS (
  SELECT 'model.health.component.'||lower(component_code) AS resource_key
  FROM analytics.marketcore_model_health_component_v1
  WHERE model_health_snapshot_id=${snapshot_id}
  UNION ALL
  SELECT 'model.health.gate.'||lower(gate_status) AS resource_key
  FROM analytics.marketcore_model_health_gate_v1
  WHERE model_health_snapshot_id=${snapshot_id}
  UNION ALL
  SELECT 'model.health.recommendation.'||lower(recommendation_code) AS resource_key
  FROM analytics.marketcore_model_health_recommendation_v1
  WHERE model_health_snapshot_id=${snapshot_id}
  UNION ALL
  SELECT 'model.health.reason.'||lower(recommendation_reason) AS resource_key
  FROM analytics.marketcore_model_health_recommendation_v1
  WHERE model_health_snapshot_id=${snapshot_id}
  UNION ALL
  SELECT 'model.health.action.'||lower(recommended_action) AS resource_key
  FROM analytics.marketcore_model_health_recommendation_v1
  WHERE model_health_snapshot_id=${snapshot_id}
)
SELECT count(*)
FROM keys k
LEFT JOIN presentation.ui_resource_v1 r
  ON r.resource_key=k.resource_key
 AND r.locale_code='ru'
WHERE r.resource_key IS NULL;
")

echo "components=${components}"
echo "gates=${gates}"
echo "recommendations=${recommendations}"
echo "bad_status=${bad_status}"
echo "bad_gate=${bad_gate}"
echo "unsafe_rows=${unsafe}"
echo "missing_i18n=${missing_i18n}"

test "$components" -ge 8
test "$gates" -ge 4
test "$recommendations" -ge 1
test "$bad_status" = "0"
test "$bad_gate" = "0"
test "$unsafe" = "0"
test "$missing_i18n" = "0"

echo
echo "=== SAFETY ==="
echo "approved=0"
echo "applied=0"
echo "auto_decision=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo

echo "VERDICT=MARKETCORE_MODEL_HEALTH_AUDIT_V1_READY"
} | tee "$report"

grep -q "VERDICT=MARKETCORE_MODEL_HEALTH_AUDIT_V1_READY" "$report"

echo "report=$report"
echo "mode=read_only_audit"
echo "model_health_snapshot_id=$snapshot_id"
echo "approved=0"
echo "applied=0"
echo "auto_decision=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_MODEL_HEALTH_AUDIT_V1_READY"
echo "VERDICT=TEST_MARKETCORE_MODEL_HEALTH_AUDIT_V1_OK"
