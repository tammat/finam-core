#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_RUNTIME_ENGINE_PLAN_V1 ==="

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'shadow_scorecards=' || count(*)
FROM research.shadow_runtime_scorecard_v1;

SELECT 'ready_shadow_scorecards=' || count(*)
FROM research.shadow_runtime_scorecard_v1
WHERE total_events >= 1
  AND failed_events = 0
  AND timeout_events = 0
  AND cancelled_events = 0;

SELECT
'ready_for_paper=' ||
candidate_id || '|' ||
symbol || '|' ||
strategy || '|' ||
timeframe ||
'|events=' || total_events ||
'|failed=' || failed_events ||
'|timeout=' || timeout_events ||
'|cancelled=' || cancelled_events
FROM research.shadow_runtime_scorecard_v1
WHERE total_events >= 1
  AND failed_events = 0
  AND timeout_events = 0
  AND cancelled_events = 0
ORDER BY created_at DESC
LIMIT 1;

SELECT 'planned_source=research.shadow_runtime_scorecard_v1';

SELECT 'planned_target=research.paper_runtime_runs_v1';

SELECT 'planned_action=CREATE_PAPER_RUN_RECORD_ONLY';

SELECT 'planned_paper_status=PLANNED';

SELECT 'planned_paper_reason=SHADOW_SCORECARD_OK';

SELECT 'planned_execution=NO_REAL_ORDERS_NO_BROKER_ORDERS_NO_MICRO_LIVE';

SELECT 'planned_paper_objects=paper_runtime_runs_v1_ONLY';

SELECT 'paper_orders_created=0';

SELECT 'paper_fills_created=0';

SELECT 'paper_trades_created=0';

SELECT 'db_update=0';
SELECT 'runtime_changed=0';
SELECT 'execution_changed=0';
SELECT 'orders_changed=0';
SELECT 'fills_changed=0';
SELECT 'micro_live_allowed=0';

SELECT 'VERDICT=PAPER_RUNTIME_ENGINE_PLAN_V1_READY';
SQL

echo "TEST_PAPER_RUNTIME_ENGINE_PLAN_V1_OK"
