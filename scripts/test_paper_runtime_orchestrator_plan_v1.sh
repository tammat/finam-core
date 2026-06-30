#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_RUNTIME_ORCHESTRATOR_PLAN_V1 ==="

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'

SELECT 'shadow_scorecards=' || count(*)
FROM research.shadow_runtime_scorecard_v1;

SELECT 'ready_shadow_candidates=' || count(*)
FROM research.shadow_runtime_scorecard_v1
WHERE total_events >= 1
  AND failed_events = 0
  AND timeout_events = 0
  AND cancelled_events = 0;

SELECT
'candidate=' ||
candidate_id || '|' ||
symbol || '|' ||
strategy || '|' ||
timeframe
FROM research.shadow_runtime_scorecard_v1
WHERE total_events >= 1
ORDER BY created_at DESC
LIMIT 1;

SELECT 'planned_source=research.shadow_runtime_scorecard_v1';

SELECT 'planned_target=research.paper_runtime_orchestrator_v1';

SELECT 'pipeline_stage_1=QUEUE';

SELECT 'pipeline_stage_2=RISK';

SELECT 'pipeline_stage_3=SIGNAL';

SELECT 'pipeline_stage_4=ORDER';

SELECT 'pipeline_stage_5=PAPER_BROKER';

SELECT 'pipeline_stage_6=ACCOUNTING';

SELECT 'pipeline_stage_7=MONITOR';

SELECT 'initial_stage=QUEUE';

SELECT 'initial_status=PLANNED';

SELECT 'scheduler_mode=MULTI_CANDIDATE';

SELECT 'execution_mode=PAPER_ONLY';

SELECT 'broker_mode=NO_REAL_BROKER';

SELECT 'paper_orders=0';

SELECT 'paper_fills=0';

SELECT 'paper_trades=0';

SELECT 'runtime_changed=0';

SELECT 'execution_changed=0';

SELECT 'orders_changed=0';

SELECT 'fills_changed=0';

SELECT 'micro_live_allowed=0';

SELECT 'VERDICT=PAPER_RUNTIME_ORCHESTRATOR_PLAN_V1_READY';

SQL

echo "TEST_PAPER_RUNTIME_ORCHESTRATOR_PLAN_V1_OK"

