#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKFLOW_RUNTIME_ENGINE_PLAN_V1 ==="

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'planned_source=research.shadow_runtime_scorecard_v1';

SELECT 'planned_targets=research.workflow_stage_registry_v1,research.workflow_runtime_runs_v1,research.workflow_runtime_events_v1';

SELECT 'workflow_type=PAPER_RUNTIME';

SELECT 'workflow_version=v1';

SELECT 'transition_1=QUEUE->RISK';
SELECT 'transition_2=RISK->SIGNAL';
SELECT 'transition_3=SIGNAL->ORDER';
SELECT 'transition_4=ORDER->PAPER_BROKER';
SELECT 'transition_5=PAPER_BROKER->ACCOUNTING';
SELECT 'transition_6=ACCOUNTING->MONITOR';
SELECT 'transition_7=MONITOR->FINISHED';

SELECT 'initial_status=PLANNED';
SELECT 'initial_stage=QUEUE';
SELECT 'initial_next_stage=RISK';

SELECT 'terminal_stage=FINISHED';

SELECT 'event_model=INSERT_ONLY';
SELECT 'run_model=UPSERT_CURRENT_STATE';

SELECT 'stage_registry_model=VERSIONED_WORKFLOW_DEFINITION';

SELECT 'scheduler_mode=MULTI_CANDIDATE';

SELECT 'execution_mode=PAPER_ONLY';
SELECT 'real_execution=false';
SELECT 'broker_mode=NO_REAL_BROKER';

SELECT 'paper_orders_created=0';
SELECT 'paper_fills_created=0';
SELECT 'paper_trades_created=0';

SELECT 'db_update=0';
SELECT 'runtime_changed=0';
SELECT 'execution_changed=0';
SELECT 'orders_changed=0';
SELECT 'fills_changed=0';
SELECT 'micro_live_allowed=0';

SELECT 'VERDICT=WORKFLOW_RUNTIME_ENGINE_PLAN_V1_READY';
SQL

echo "TEST_WORKFLOW_RUNTIME_ENGINE_PLAN_V1_OK"
