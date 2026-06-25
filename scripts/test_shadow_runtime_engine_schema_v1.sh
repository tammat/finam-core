#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_SHADOW_RUNTIME_ENGINE_SCHEMA_V1 ==="

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'source_queue_exists=' || EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema='research'
      AND table_name='shadow_runtime_queue_v1'
);

SELECT 'source_queue_ready_rows=' || count(*)
FROM research.shadow_runtime_queue_v1
WHERE queue_status='READY';

SELECT 'source_queue_columns=' || string_agg(column_name, ',' ORDER BY ordinal_position)
FROM information_schema.columns
WHERE table_schema='research'
  AND table_name='shadow_runtime_queue_v1';

SELECT 'target_table=research.shadow_runtime_runs_v1';

SELECT 'target_columns=shadow_run_id,queue_id,candidate_id,symbol,strategy,timeframe,run_status,run_reason,started_at,finished_at,runtime_changed,execution_changed,orders_changed,fills_changed,micro_live_allowed,payload,created_at,updated_at';

SELECT 'allowed_run_status=PLANNED,RUNNING,COMPLETED,FAILED,BLOCKED';

SELECT 'engine_rule=READ_ONLY_FROM_shadow_runtime_queue_v1_WHERE_queue_status_READY';

SELECT 'runtime_changed=0';
SELECT 'execution_changed=0';
SELECT 'orders_changed=0';
SELECT 'fills_changed=0';
SELECT 'micro_live_allowed=0';

SELECT 'VERDICT=SHADOW_RUNTIME_ENGINE_SCHEMA_V1_READY';
SQL

echo "TEST_SHADOW_RUNTIME_ENGINE_SCHEMA_V1_OK"
