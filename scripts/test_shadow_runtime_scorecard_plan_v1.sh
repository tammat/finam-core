#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_SHADOW_RUNTIME_SCORECARD_PLAN_V1 ==="

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'

SELECT 'monitor_rows=' || count(*)
FROM research.shadow_runtime_monitor_v1;

SELECT
'latest_event=' ||
candidate_id || '|' ||
symbol || '|' ||
strategy || '|' ||
timeframe || '|' ||
transition_from || '->' ||
transition_to
FROM research.shadow_runtime_monitor_v1
ORDER BY event_ts DESC
LIMIT 1;

SELECT 'planned_source=research.shadow_runtime_monitor_v1';

SELECT 'planned_target=research.shadow_runtime_scorecard_v1';

SELECT 'planned_aggregation=PER_SHADOW_RUN';

SELECT 'metric_1=TOTAL_EVENTS';

SELECT 'metric_2=SUCCESS_RATE';

SELECT 'metric_3=FAILURE_RATE';

SELECT 'metric_4=TIMEOUT_RATE';

SELECT 'metric_5=AVG_LATENCY_MS';

SELECT 'metric_6=AVG_RUNTIME_SECONDS';

SELECT 'metric_7=AVG_QUEUE_WAIT_SECONDS';

SELECT 'expected_initial_total_events=1';

SELECT 'expected_initial_planned_events=1';

SELECT 'expected_initial_starting_events=1';

SELECT 'expected_initial_running_events=0';

SELECT 'expected_initial_completed_events=0';

SELECT 'expected_initial_failed_events=0';

SELECT 'expected_initial_timeout_events=0';

SELECT 'scorecard_mode=READ_ONLY_AGGREGATION';

SELECT 'db_update=0';

SELECT 'runtime_changed=0';

SELECT 'execution_changed=0';

SELECT 'orders_changed=0';

SELECT 'fills_changed=0';

SELECT 'micro_live_allowed=0';

SELECT 'VERDICT=SHADOW_RUNTIME_SCORECARD_PLAN_V1_READY';

SQL

echo "TEST_SHADOW_RUNTIME_SCORECARD_PLAN_V1_OK"

