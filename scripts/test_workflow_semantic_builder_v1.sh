#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKFLOW_SEMANTIC_BUILDER_V1 ==="

PYTHONPATH=src src/scripts/research/build_workflow_semantic_builder_v1.py --save \
  | tee /tmp/workflow_semantic_builder_v1.out

grep -q "WORKFLOW_SEMANTIC_BUILDER_V1" /tmp/workflow_semantic_builder_v1.out
grep -q "mode=save" /tmp/workflow_semantic_builder_v1.out
grep -q "sem_candidate_total=1" /tmp/workflow_semantic_builder_v1.out
grep -q "sem_workflow_total=1" /tmp/workflow_semantic_builder_v1.out
grep -q "sem_candidate=MSC-000001" /tmp/workflow_semantic_builder_v1.out
grep -q "sem_workflow=" /tmp/workflow_semantic_builder_v1.out
grep -q "presentation_ready=1" /tmp/workflow_semantic_builder_v1.out
grep -q "mart_reads=SEMANTIC_ONLY" /tmp/workflow_semantic_builder_v1.out
grep -q "ui_reads=MART_OR_SNAPSHOT_ONLY" /tmp/workflow_semantic_builder_v1.out
grep -q "decision_logic_policy=NO_DECISION_LOGIC_IN_SEMANTIC_LAYER" /tmp/workflow_semantic_builder_v1.out
grep -q "runtime_changed=0" /tmp/workflow_semantic_builder_v1.out
grep -q "execution_changed=0" /tmp/workflow_semantic_builder_v1.out
grep -q "orders_changed=0" /tmp/workflow_semantic_builder_v1.out
grep -q "fills_changed=0" /tmp/workflow_semantic_builder_v1.out
grep -q "micro_live_allowed=0" /tmp/workflow_semantic_builder_v1.out
grep -q "VERDICT=WORKFLOW_SEMANTIC_BUILDER_V1_READY" /tmp/workflow_semantic_builder_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'sem_candidate_rows=' || count(*)
FROM warehouse.sem_candidate_v1;

SELECT 'sem_workflow_rows=' || count(*)
FROM warehouse.sem_workflow_v1;

SELECT 'sem_candidate_latest=' ||
       candidate_id || '|' ||
       workflow_status_code || '|' ||
       current_stage_code || '|' ||
       current_stage_label_ru || '|' ||
       coalesce(next_stage_code,'NULL') || '|' ||
       next_stage_label_ru || '|' ||
       health_light || '|' ||
       health_icon
FROM warehouse.sem_candidate_v1
ORDER BY updated_at DESC
LIMIT 1;

SELECT 'sem_workflow_latest=' ||
       workflow_run_id || '|' ||
       candidate_id || '|' ||
       workflow_status_code || '|' ||
       current_stage_code || '|' ||
       current_stage_label_ru || '|' ||
       coalesce(next_stage_code,'NULL') || '|' ||
       next_stage_label_ru || '|' ||
       health_light || '|' ||
       health_icon
FROM warehouse.sem_workflow_v1
ORDER BY updated_at DESC
LIMIT 1;
SQL

echo "TEST_WORKFLOW_SEMANTIC_BUILDER_V1_OK"
