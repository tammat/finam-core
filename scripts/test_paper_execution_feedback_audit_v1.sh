#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_EXECUTION_FEEDBACK_AUDIT_V1 ==="

mkdir -p reports
report="reports/paper_execution_feedback_audit_v1.txt"

{
echo "======================================================"
echo "PAPER EXECUTION FEEDBACK AUDIT V1"
echo "======================================================"
echo "generated_at=$(date -Is)"
echo

echo "=== FEEDBACK SUMMARY ==="
psql -d finam_core -P pager=off -c "
SELECT
  count(*) AS rows_total,
  count(DISTINCT analytics_snapshot_id) AS analytics_snapshots,
  count(DISTINCT robustness_snapshot_id) AS robustness_snapshots,
  count(DISTINCT feedback_scope_code) AS scopes,
  count(DISTINCT feedback_reason_code) AS reasons,
  count(DISTINCT feedback_severity_code) AS severities,
  count(DISTINCT recommended_action_code) AS actions
FROM analytics.paper_execution_feedback_v1
WHERE source_version='PAPER_EXECUTION_FEEDBACK_ENGINE_V1';
"

echo
echo "=== FEEDBACK BY SCOPE ==="
psql -d finam_core -P pager=off -c "
SELECT
  feedback_scope_code,
  count(*) AS rows_total
FROM analytics.paper_execution_feedback_v1
WHERE source_version='PAPER_EXECUTION_FEEDBACK_ENGINE_V1'
GROUP BY feedback_scope_code
ORDER BY rows_total DESC, feedback_scope_code;
"

echo
echo "=== FEEDBACK BY REASON ==="
psql -d finam_core -P pager=off -c "
SELECT
  feedback_reason_code,
  feedback_severity_code,
  recommended_action_code,
  count(*) AS rows_total
FROM analytics.paper_execution_feedback_v1
WHERE source_version='PAPER_EXECUTION_FEEDBACK_ENGINE_V1'
GROUP BY feedback_reason_code, feedback_severity_code, recommended_action_code
ORDER BY rows_total DESC, feedback_reason_code;
"

echo
echo "=== FEEDBACK QUEUE ==="
psql -d finam_core -P pager=off -c "
SELECT
  feedback_id,
  feedback_scope_code,
  feedback_target,
  feedback_reason_code,
  feedback_severity_code,
  recommended_action_code,
  sample_status,
  confidence,
  approved,
  applied,
  auto_decision,
  created_at
FROM analytics.paper_execution_feedback_v1
WHERE source_version='PAPER_EXECUTION_FEEDBACK_ENGINE_V1'
ORDER BY created_at DESC, feedback_id DESC
LIMIT 30;
"

echo
echo "=== FK VALIDATION ==="
psql -d finam_core -P pager=off -c "
SELECT
  count(*) AS bad_fk_rows
FROM analytics.paper_execution_feedback_v1 f
LEFT JOIN analytics.analytics_snapshot_v1 a
  ON a.analytics_snapshot_id=f.analytics_snapshot_id
LEFT JOIN analytics.analytics_snapshot_v1 rbs
  ON rbs.analytics_snapshot_id=f.robustness_snapshot_id
LEFT JOIN analytics.paper_execution_feedback_scope_v1 s
  ON s.feedback_scope_code=f.feedback_scope_code
LEFT JOIN analytics.paper_execution_feedback_action_v1 a2
  ON a2.feedback_action_code=f.recommended_action_code
LEFT JOIN analytics.paper_execution_feedback_reason_v1 rr
  ON rr.reason_code=f.feedback_reason_code
LEFT JOIN analytics.paper_execution_feedback_severity_v1 sv
  ON sv.severity_code=f.feedback_severity_code
WHERE f.source_version='PAPER_EXECUTION_FEEDBACK_ENGINE_V1'
  AND (
       a.analytics_snapshot_id IS NULL
    OR rbs.analytics_snapshot_id IS NULL
    OR s.feedback_scope_code IS NULL
    OR a2.feedback_action_code IS NULL
    OR rr.reason_code IS NULL
    OR sv.severity_code IS NULL
  );
"

echo
echo "=== I18N VALIDATION ==="
psql -d finam_core -P pager=off -c "
WITH keys AS (
  SELECT 'paper.feedback.reason.'||lower(reason_code) AS resource_key
  FROM analytics.paper_execution_feedback_reason_v1
  WHERE enabled
  UNION ALL
  SELECT 'paper.feedback.severity.'||lower(severity_code) AS resource_key
  FROM analytics.paper_execution_feedback_severity_v1
  WHERE enabled
  UNION ALL
  SELECT 'paper.feedback.reason_group.'||lower(reason_group_code) AS resource_key
  FROM analytics.paper_execution_feedback_reason_group_v1
  WHERE enabled
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
FROM analytics.paper_execution_feedback_v1
WHERE source_version='PAPER_EXECUTION_FEEDBACK_ENGINE_V1';
"

echo
echo "=== AUDIT DECISION ==="

rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.paper_execution_feedback_v1
WHERE source_version='PAPER_EXECUTION_FEEDBACK_ENGINE_V1';
")

bad_fk=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.paper_execution_feedback_v1 f
LEFT JOIN analytics.analytics_snapshot_v1 a
  ON a.analytics_snapshot_id=f.analytics_snapshot_id
LEFT JOIN analytics.analytics_snapshot_v1 rbs
  ON rbs.analytics_snapshot_id=f.robustness_snapshot_id
LEFT JOIN analytics.paper_execution_feedback_scope_v1 s
  ON s.feedback_scope_code=f.feedback_scope_code
LEFT JOIN analytics.paper_execution_feedback_action_v1 a2
  ON a2.feedback_action_code=f.recommended_action_code
LEFT JOIN analytics.paper_execution_feedback_reason_v1 rr
  ON rr.reason_code=f.feedback_reason_code
LEFT JOIN analytics.paper_execution_feedback_severity_v1 sv
  ON sv.severity_code=f.feedback_severity_code
WHERE f.source_version='PAPER_EXECUTION_FEEDBACK_ENGINE_V1'
  AND (
       a.analytics_snapshot_id IS NULL
    OR rbs.analytics_snapshot_id IS NULL
    OR s.feedback_scope_code IS NULL
    OR a2.feedback_action_code IS NULL
    OR rr.reason_code IS NULL
    OR sv.severity_code IS NULL
  );
")

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.paper_execution_feedback_v1
WHERE source_version='PAPER_EXECUTION_FEEDBACK_ENGINE_V1'
  AND (
       approved<>0
    OR applied<>0
    OR auto_decision<>0
  );
")

missing_i18n=$(psql -At -d finam_core -c "
WITH keys AS (
  SELECT 'paper.feedback.reason.'||lower(reason_code) AS resource_key
  FROM analytics.paper_execution_feedback_reason_v1
  WHERE enabled
  UNION ALL
  SELECT 'paper.feedback.severity.'||lower(severity_code) AS resource_key
  FROM analytics.paper_execution_feedback_severity_v1
  WHERE enabled
  UNION ALL
  SELECT 'paper.feedback.reason_group.'||lower(reason_group_code) AS resource_key
  FROM analytics.paper_execution_feedback_reason_group_v1
  WHERE enabled
)
SELECT count(*)
FROM keys k
LEFT JOIN presentation.ui_resource_v1 r
  ON r.resource_key=k.resource_key
 AND r.locale_code='ru'
WHERE r.resource_key IS NULL;
")

echo "feedback_rows=${rows}"
echo "bad_fk_rows=${bad_fk}"
echo "unsafe_rows=${unsafe}"
echo "missing_i18n_resources=${missing_i18n}"

if [ "$rows" -lt 1 ]; then
  echo "FEEDBACK_ROWS_MISSING"
  exit 1
fi

if [ "$bad_fk" != "0" ]; then
  echo "BAD_FK_ROWS=$bad_fk"
  exit 1
fi

if [ "$unsafe" != "0" ]; then
  echo "UNSAFE_FEEDBACK_ROWS=$unsafe"
  exit 1
fi

if [ "$missing_i18n" != "0" ]; then
  echo "MISSING_I18N_RESOURCES=$missing_i18n"
  exit 1
fi

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

echo "VERDICT=PAPER_EXECUTION_FEEDBACK_AUDIT_V1_READY"
} | tee "$report"

grep -q "VERDICT=PAPER_EXECUTION_FEEDBACK_AUDIT_V1_READY" "$report"

echo "report=$report"
echo "mode=read_only_audit"
echo "approved=0"
echo "applied=0"
echo "auto_decision=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PAPER_EXECUTION_FEEDBACK_AUDIT_V1_READY"
echo "VERDICT=TEST_PAPER_EXECUTION_FEEDBACK_AUDIT_V1_OK"
