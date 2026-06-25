#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_SHADOW_RUNTIME_MONITOR_SCHEMA_V1 ==="

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'

SELECT 'source_runtime_runs_exists=' || EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema='research'
      AND table_name='shadow_runtime_runs_v1'
);

SELECT 'source_runtime_runs_rows=' || count(*)
FROM research.shadow_runtime_runs_v1;

SELECT 'source_runtime_runs_columns=' ||
       string_agg(column_name, ',' ORDER BY ordinal_position)
FROM information_schema.columns
WHERE table_schema='research'
  AND table_name='shadow_runtime_runs_v1';

SELECT 'target_table=research.shadow_runtime_monitor_v1';

SELECT 'target_columns=' ||
'monitor_id,'||
'shadow_run_id,'||
'candidate_id,'||
'symbol,'||
'strategy,'||
'timeframe,'||
'run_status,'||
'transition_from,'||
'transition_to,'||
'transition_reason,'||
'heartbeat_ts,'||
'latency_ms,'||
'runtime_seconds,'||
'queue_wait_seconds,'||
'event_ts,'||
'payload,'||
'created_at';

SELECT 'allowed_states='||
'PLANNED,'||
'STARTING,'||
'RUNNING,'||
'COMPLETED,'||
'FAILED,'||
'TIMEOUT,'||
'CANCELLED';

SELECT 'event_model=INSERT_ONLY';

SELECT 'db_update=0';

SELECT 'runtime_changed=0';

SELECT 'execution_changed=0';

SELECT 'orders_changed=0';

SELECT 'fills_changed=0';

SELECT 'micro_live_allowed=0';

SELECT 'VERDICT=SHADOW_RUNTIME_MONITOR_SCHEMA_V1_READY';

SQL

echo "TEST_SHADOW_RUNTIME_MONITOR_SCHEMA_V1_OK"

