#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_SIGNAL_FUNNEL_REASON_INVENTORY_V1 ==="

mkdir -p reports
report="reports/signal_funnel_reason_inventory_v1.txt"

{
echo "======================================================"
echo "SIGNAL FUNNEL REASON INVENTORY V1"
echo "======================================================"
echo "generated_at=$(date -Is)"
echo

echo "=== REASON / DECISION / STATUS COLUMNS ==="
psql -d finam_core -P pager=off <<'SQL'
SELECT
    table_schema,
    table_name,
    column_name,
    data_type
FROM information_schema.columns
WHERE table_schema IN ('analytics','knowledge','public')
  AND (
       lower(column_name) LIKE '%reason%'
    OR lower(column_name) LIKE '%status%'
    OR lower(column_name) LIKE '%decision%'
    OR lower(column_name) LIKE '%reject%'
    OR lower(column_name) LIKE '%block%'
    OR lower(column_name) LIKE '%gate%'
    OR lower(column_name) LIKE '%verdict%'
    OR lower(column_name) LIKE '%allow%'
    OR lower(column_name) LIKE '%enabled%'
    OR lower(column_name) LIKE '%approved%'
    OR lower(column_name) LIKE '%applied%'
  )
  AND (
       lower(table_name) LIKE '%signal%'
    OR lower(table_name) LIKE '%runtime%'
    OR lower(table_name) LIKE '%candidate%'
    OR lower(table_name) LIKE '%governance%'
    OR lower(table_name) LIKE '%recommend%'
    OR lower(table_name) LIKE '%paper%'
    OR lower(table_name) LIKE '%execution%'
    OR lower(table_name) LIKE '%order%'
    OR lower(table_name) LIKE '%trade%'
    OR lower(table_name) LIKE '%risk%'
    OR lower(table_name) LIKE '%guard%'
  )
ORDER BY table_schema, table_name, ordinal_position;
SQL

echo
echo "=== HIGH VALUE TABLE ROW COUNTS ==="
psql -d finam_core -P pager=off <<'SQL'
WITH target(table_schema, table_name) AS (
  VALUES
    ('public','runtime_guard_signal_registry_v1'),
    ('public','runtime_candidate_decision_board'),
    ('public','runtime_candidate_lifecycle_board'),
    ('public','runtime_governance_decisions'),
    ('analytics','paper_execution_feedback_v1'),
    ('analytics','recommendation_feedback_v1'),
    ('public','execution_state_transitions'),
    ('public','signal_lifecycle'),
    ('public','trade_context_snapshots'),
    ('public','runtime_guard_pre_signal_block_audit_v1'),
    ('public','trusted_runtime_gate_v1'),
    ('knowledge','recommendation_v1'),
    ('knowledge','recommendation_result_v1'),
    ('knowledge','recommendation_execution_context_v1')
)
SELECT
  t.table_schema,
  t.table_name,
  CASE WHEN c.oid IS NULL THEN 'MISSING' ELSE 'EXISTS' END AS table_status
FROM target t
LEFT JOIN pg_namespace n
  ON n.nspname=t.table_schema
LEFT JOIN pg_class c
  ON c.relnamespace=n.oid
 AND c.relname=t.table_name
ORDER BY t.table_schema, t.table_name;
SQL

echo
echo "=== SAMPLE DISTINCT VALUES FROM KNOWN FEEDBACK TABLE ==="
psql -d finam_core -P pager=off <<'SQL'
SELECT
  feedback_reason_code,
  feedback_severity_code,
  recommended_action_code,
  count(*) AS rows_total
FROM analytics.paper_execution_feedback_v1
GROUP BY feedback_reason_code, feedback_severity_code, recommended_action_code
ORDER BY rows_total DESC, feedback_reason_code
LIMIT 50;
SQL

echo
echo "=== CANDIDATE REASON TABLES WITH ROW COUNTS ==="
psql -d finam_core -P pager=off <<'SQL'
WITH candidate_tables AS (
  SELECT DISTINCT
      c.table_schema,
      c.table_name
  FROM information_schema.columns c
  WHERE c.table_schema IN ('analytics','knowledge','public')
    AND (
         lower(c.column_name) LIKE '%reason%'
      OR lower(c.column_name) LIKE '%status%'
      OR lower(c.column_name) LIKE '%decision%'
      OR lower(c.column_name) LIKE '%reject%'
      OR lower(c.column_name) LIKE '%block%'
      OR lower(c.column_name) LIKE '%gate%'
      OR lower(c.column_name) LIKE '%verdict%'
    )
    AND (
         lower(c.table_name) LIKE '%signal%'
      OR lower(c.table_name) LIKE '%runtime%'
      OR lower(c.table_name) LIKE '%candidate%'
      OR lower(c.table_name) LIKE '%governance%'
      OR lower(c.table_name) LIKE '%recommend%'
      OR lower(c.table_name) LIKE '%paper%'
      OR lower(c.table_name) LIKE '%execution%'
      OR lower(c.table_name) LIKE '%order%'
      OR lower(c.table_name) LIKE '%trade%'
      OR lower(c.table_name) LIKE '%risk%'
      OR lower(c.table_name) LIKE '%guard%'
    )
)
SELECT
    table_schema,
    table_name
FROM candidate_tables
ORDER BY table_schema, table_name;
SQL

echo
echo "=== SAFETY ==="
echo "mode=read_only_inventory"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo
echo "VERDICT=SIGNAL_FUNNEL_REASON_INVENTORY_V1_READY"
} | tee "$report"

grep -q "VERDICT=SIGNAL_FUNNEL_REASON_INVENTORY_V1_READY" "$report"
grep -q "paper_execution_feedback_v1" "$report"

echo "report=$report"
echo "mode=read_only_inventory"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=SIGNAL_FUNNEL_REASON_INVENTORY_V1_READY"
echo "VERDICT=TEST_SIGNAL_FUNNEL_REASON_INVENTORY_V1_OK"
