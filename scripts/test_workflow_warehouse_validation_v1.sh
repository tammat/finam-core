#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKFLOW_WAREHOUSE_VALIDATION_V1 ==="

PYTHONPATH=src src/scripts/research/build_workflow_warehouse_validation_v1.py \
  | tee /tmp/workflow_warehouse_validation_v1.out

grep -q "WORKFLOW_WAREHOUSE_VALIDATION_V1" /tmp/workflow_warehouse_validation_v1.out
grep -q "qlt_event_rows=" /tmp/workflow_warehouse_validation_v1.out
grep -q "nrm_event_rows=" /tmp/workflow_warehouse_validation_v1.out
grep -q "event_stage_fact_rows=" /tmp/workflow_warehouse_validation_v1.out
grep -q "state_lifecycle_rows=" /tmp/workflow_warehouse_validation_v1.out
grep -q "dim_stage_rows=" /tmp/workflow_warehouse_validation_v1.out
grep -q "sem_candidate_rows=" /tmp/workflow_warehouse_validation_v1.out
grep -q "mart_dashboard_rows=9" /tmp/workflow_warehouse_validation_v1.out
grep -q "snap_today_rows=9" /tmp/workflow_warehouse_validation_v1.out
grep -q "candidate_latest=MSC-000001" /tmp/workflow_warehouse_validation_v1.out
grep -q "workflow_warehouse_v1_complete=1" /tmp/workflow_warehouse_validation_v1.out
grep -q "runtime_changed=0" /tmp/workflow_warehouse_validation_v1.out
grep -q "execution_changed=0" /tmp/workflow_warehouse_validation_v1.out
grep -q "orders_changed=0" /tmp/workflow_warehouse_validation_v1.out
grep -q "fills_changed=0" /tmp/workflow_warehouse_validation_v1.out
grep -q "micro_live_allowed=0" /tmp/workflow_warehouse_validation_v1.out
grep -q "VERDICT=WORKFLOW_WAREHOUSE_VALIDATION_V1_READY" /tmp/workflow_warehouse_validation_v1.out

curl -fsS http://127.0.0.1:8089/ >/tmp/read_only_ui_validation_v1.html
grep -q "Finam Core" /tmp/read_only_ui_validation_v1.html
grep -q "Портфель" /tmp/read_only_ui_validation_v1.html
grep -q "Кандидат" /tmp/read_only_ui_validation_v1.html

echo "read_only_ui_http=200"
echo "TEST_WORKFLOW_WAREHOUSE_VALIDATION_V1_OK"
