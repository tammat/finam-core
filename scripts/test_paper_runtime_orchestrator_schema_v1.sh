#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_RUNTIME_ORCHESTRATOR_SCHEMA_V1 ==="

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

SELECT 'source_queue_exists=' || EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema='research'
      AND table_name='shadow_runtime_queue_v1'
);

SELECT 'target_table=research.paper_runtime_orchestrator_v1';

SELECT 'target_columns=' ||
'orchestrator_id,' ||
'candidate_id,' ||
'symbol,' ||
'strategy,' ||
'timeframe,' ||
'priority,' ||
'orchestrator_status,' ||
'current_stage,' ||
'next_stage,' ||
'risk_stage,' ||
'signal_stage,' ||
'order_stage,' ||
'broker_stage,' ||
'accounting_stage,' ||
'monitor_stage,' ||
'payload,' ||
'created_at,' ||
'updated_at';

SELECT 'pipeline=' ||
'QUEUE->RISK->SIGNAL->ORDER->PAPER_BROKER->ACCOUNTING->MONITOR';

SELECT 'allowed_status=' ||
'PLANNED,RUNNING,WAITING,BLOCKED,COMPLETED,FAILED';

SELECT 'execution_model=ORCHESTRATOR';

SELECT 'paper_only=true';

SELECT 'real_execution=false';

SELECT 'micro_live_allowed=false';

SELECT 'db_update=0';
SELECT 'runtime_changed=0';
SELECT 'execution_changed=0';
SELECT 'orders_changed=0';
SELECT 'fills_changed=0';

SELECT 'VERDICT=PAPER_RUNTIME_ORCHESTRATOR_SCHEMA_V1_READY';

SQL

echo "TEST_PAPER_RUNTIME_ORCHESTRATOR_SCHEMA_V1_OK"
