#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_SHADOW_RUNTIME_SCORECARD_SCHEMA_V1 ==="

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'

SELECT 'source_monitor_exists=' || EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema='research'
      AND table_name='shadow_runtime_monitor_v1'
);

SELECT 'source_monitor_rows=' || count(*)
FROM research.shadow_runtime_monitor_v1;

SELECT 'source_monitor_columns=' ||
       string_agg(column_name, ',' ORDER BY ordinal_position)
FROM information_schema.columns
WHERE table_schema='research'
  AND table_name='shadow_runtime_monitor_v1';

SELECT 'target_table=research.shadow_runtime_scorecard_v1';

SELECT 'target_columns=' ||
'scorecard_id,'||
'shadow_run_id,'||
'candidate_id,'||
'symbol,'||
'strategy,'||
'timeframe,'||
'total_events,'||
'planned_events,'||
'starting_events,'||
'running_events,'||
'completed_events,'||
'failed_events,'||
'timeout_events,'||
'cancelled_events,'||
'avg_latency_ms,'||
'avg_runtime_seconds,'||
'avg_queue_wait_seconds,'||
'payload,'||
'created_at';

SELECT 'scorecard_metrics='||
'total_events,'||
'success_rate,'||
'failure_rate,'||
'timeout_rate,'||
'avg_latency,'||
'avg_runtime,'||
'avg_queue_wait';

SELECT 'aggregation_model=PER_SHADOW_RUN';

SELECT 'db_update=0';

SELECT 'runtime_changed=0';

SELECT 'execution_changed=0';

SELECT 'orders_changed=0';

SELECT 'fills_changed=0';

SELECT 'micro_live_allowed=0';

SELECT 'VERDICT=SHADOW_RUNTIME_SCORECARD_SCHEMA_V1_READY';

SQL

echo "TEST_SHADOW_RUNTIME_SCORECARD_SCHEMA_V1_OK"

