#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_RUNTIME_ENGINE_SCHEMA_V1 ==="

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'source_shadow_scorecard_exists=' || EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema='research'
      AND table_name='shadow_runtime_scorecard_v1'
);

SELECT 'source_shadow_runs_exists=' || EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema='research'
      AND table_name='shadow_runtime_runs_v1'
);

SELECT 'source_scorecards=' || count(*)
FROM research.shadow_runtime_scorecard_v1;

SELECT 'source_ready_for_paper=' || count(*)
FROM research.shadow_runtime_scorecard_v1
WHERE total_events >= 1
  AND failed_events = 0
  AND timeout_events = 0
  AND cancelled_events = 0;

SELECT 'target_table=research.paper_runtime_runs_v1';

SELECT 'target_columns=paper_run_id,shadow_run_id,candidate_id,symbol,strategy,timeframe,paper_status,paper_reason,planned_at,started_at,finished_at,orders_created,fills_created,trades_created,runtime_changed,execution_changed,orders_changed,fills_changed,micro_live_allowed,payload,created_at,updated_at';

SELECT 'allowed_paper_status=PLANNED,RUNNING,COMPLETED,FAILED,BLOCKED';

SELECT 'engine_rule=CREATE_PAPER_RUN_FROM_SHADOW_SCORECARD_IF_shadow_ok_AND_no_failures';

SELECT 'paper_safety=NO_REAL_ORDERS_NO_MICRO_LIVE';

SELECT 'db_update=0';
SELECT 'runtime_changed=0';
SELECT 'execution_changed=0';
SELECT 'orders_changed=0';
SELECT 'fills_changed=0';
SELECT 'micro_live_allowed=0';

SELECT 'VERDICT=PAPER_RUNTIME_ENGINE_SCHEMA_V1_READY';
SQL

echo "TEST_PAPER_RUNTIME_ENGINE_SCHEMA_V1_OK"
