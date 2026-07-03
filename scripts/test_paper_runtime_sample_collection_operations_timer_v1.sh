#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_TIMER_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/scripts/run_paper_runtime_sample_collection_operations_cycle_v1.py

test -f deploy/systemd/finam-paper-sample-operations.service
test -f deploy/systemd/finam-paper-sample-operations.timer

grep -q "User=postgres" deploy/systemd/finam-paper-sample-operations.service
grep -q "DATABASE_URL=postgresql:///finam_core" deploy/systemd/finam-paper-sample-operations.service
grep -q "run_paper_runtime_sample_collection_operations_cycle_v1.py" deploy/systemd/finam-paper-sample-operations.service
grep -q "OnUnitActiveSec=5min" deploy/systemd/finam-paper-sample-operations.timer
grep -q "finam-paper-sample-collection.service" deploy/systemd/finam-paper-sample-operations.service

sudo -u postgres env \
  DATABASE_URL=postgresql:///finam_core \
  PYTHONPATH=src \
  /opt/finam-core/venv/bin/python src/scripts/run_paper_runtime_sample_collection_cycle_v1.py \
  > /tmp/operations_timer_prereq_sample_cycle_v1.txt

grep -q "VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_CYCLE_V1_READY" \
  /tmp/operations_timer_prereq_sample_cycle_v1.txt

sudo -u postgres env \
  DATABASE_URL=postgresql:///finam_core \
  PYTHONPATH=src \
  /opt/finam-core/venv/bin/python src/scripts/run_paper_runtime_sample_collection_operations_cycle_v1.py \
  | tee /tmp/paper_runtime_sample_collection_operations_cycle_v1.txt

grep -q "VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_CYCLE_V1_READY" \
  /tmp/paper_runtime_sample_collection_operations_cycle_v1.txt

operations_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_runtime_sample_collection_operations_v1;")
allowed_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_runtime_sample_collection_operations_v1 WHERE micro_live_allowed=true;")
phase_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.phase_ii_paper_edge_discovery_summary_v1 WHERE id=1;")

test "$operations_rows" -gt 0
test "$allowed_rows" = "0"
test "$phase_rows" = "1"

psql -d finam_core -c "
SELECT
    operation_priority,
    operation_status,
    count(*) AS rows
FROM marketcore_ui.paper_runtime_sample_collection_operations_v1
GROUP BY operation_priority, operation_status
ORDER BY operation_priority, operation_status;
"

psql -d finam_core -c "
SELECT
    phase_result_status,
    engineering_status,
    operational_status,
    timer_health_status,
    micro_live_allowed,
    next_phase
FROM marketcore_ui.phase_ii_paper_edge_discovery_summary_v1
WHERE id=1;
"

echo "operations_rows=$operations_rows"
echo "micro_live_allowed_rows=$allowed_rows"
echo "phase_summary_rows=$phase_rows"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_TIMER_V1_READY"
echo "VERDICT=TEST_PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_TIMER_V1_OK"
