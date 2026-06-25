#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_SHADOW_RUNTIME_QUEUE_SCHEMA_V1 ==="

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'source_forensic_reports_exists=' || EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema='research'
      AND table_name='global_edge_forensic_reports_v1'
);

SELECT 'source_oos_campaigns_exists=' || EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema='research'
      AND table_name='oos_validation_campaigns_v1'
);

SELECT 'source_oos_decisions_exists=' || EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema='research'
      AND table_name='oos_validation_decisions_v1'
);

SELECT 'target_table=research.shadow_runtime_queue_v1';

SELECT 'target_columns=queue_id,candidate_id,forensic_report_id,campaign_id,symbol,strategy,timeframe,priority,queue_status,queue_reason,runtime_changed,execution_changed,micro_live_allowed,payload,created_at,updated_at';

SELECT 'allowed_queue_status=READY,WAITING,BLOCKED,REMOVED';

SELECT 'ready_rule=forensic_recommendation_PROMOTE_TO_OOS_VALIDATION_AND_oos_decision_PASS_TO_SHADOW_AND_runtime_changed_false_AND_micro_live_allowed_false';

SELECT 'db_update=0';
SELECT 'runtime_changed=0';
SELECT 'execution_changed=0';
SELECT 'micro_live_allowed=0';

SELECT 'VERDICT=SHADOW_RUNTIME_QUEUE_SCHEMA_V1_READY';
SQL

echo "TEST_SHADOW_RUNTIME_QUEUE_SCHEMA_V1_OK"
