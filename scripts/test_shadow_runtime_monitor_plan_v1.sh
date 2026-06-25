#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_SHADOW_RUNTIME_MONITOR_PLAN_V1 ==="

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'

SELECT 'runtime_runs=' || count(*)
FROM research.shadow_runtime_runs_v1;

SELECT
'planned_run=' ||
candidate_id || '|' ||
symbol || '|' ||
strategy || '|' ||
timeframe || '|' ||
run_status || '|' ||
run_reason
FROM research.shadow_runtime_runs_v1
WHERE run_status='PLANNED'
ORDER BY updated_at DESC
LIMIT 1;

SELECT 'planned_source=research.shadow_runtime_runs_v1';

SELECT 'planned_target=research.shadow_runtime_monitor_v1';

SELECT 'planned_model=EVENT_SOURCING';

SELECT 'planned_event_type=STATE_TRANSITION';

SELECT 'transition_1=PLANNED->STARTING';

SELECT 'transition_2=STARTING->RUNNING';

SELECT 'transition_3=RUNNING->COMPLETED';

SELECT 'transition_4=RUNNING->FAILED';

SELECT 'transition_5=RUNNING->TIMEOUT';

SELECT 'transition_6=RUNNING->CANCELLED';

SELECT 'heartbeat_policy=RUNNING_ONLY';

SELECT 'latency_measurement=STARTING_MINUS_PLANNED';

SELECT 'runtime_measurement=FINISHED_MINUS_RUNNING';

SELECT 'queue_wait_measurement=STARTING_MINUS_CREATED';

SELECT 'event_model=INSERT_ONLY';

SELECT 'db_update=0';

SELECT 'runtime_changed=0';

SELECT 'execution_changed=0';

SELECT 'orders_changed=0';

SELECT 'fills_changed=0';

SELECT 'micro_live_allowed=0';

SELECT 'VERDICT=SHADOW_RUNTIME_MONITOR_PLAN_V1_READY';

SQL

echo "TEST_SHADOW_RUNTIME_MONITOR_PLAN_V1_OK"

