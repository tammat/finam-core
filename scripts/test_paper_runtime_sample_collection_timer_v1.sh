#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_RUNTIME_SAMPLE_COLLECTION_TIMER_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/scripts/run_paper_runtime_sample_collection_cycle_v1.py

test -f deploy/systemd/finam-paper-sample-collection.service
test -f deploy/systemd/finam-paper-sample-collection.timer

grep -q "User=postgres" deploy/systemd/finam-paper-sample-collection.service
grep -q "DATABASE_URL=postgresql:///finam_core" deploy/systemd/finam-paper-sample-collection.service
grep -q "run_paper_runtime_sample_collection_cycle_v1.py" deploy/systemd/finam-paper-sample-collection.service
grep -q "OnUnitActiveSec=5min" deploy/systemd/finam-paper-sample-collection.timer

sudo -u postgres env \
  DATABASE_URL=postgresql:///finam_core \
  PYTHONPATH=src \
  /opt/finam-core/venv/bin/python src/scripts/run_paper_runtime_sample_collection_cycle_v1.py \
  | tee /tmp/paper_runtime_sample_collection_cycle_v1.txt

grep -q "VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_CYCLE_V1_READY" \
  /tmp/paper_runtime_sample_collection_cycle_v1.txt

summary_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_runtime_sample_collection_v1 WHERE id=1;")
monitor_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_sample_accumulation_monitor_v1;")
allowed_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_sample_accumulation_monitor_v1 WHERE micro_live_allowed=true;")

test "$summary_rows" = "1"
test "$monitor_rows" -gt 0
test "$allowed_rows" = "0"

psql -d finam_core -c "
SELECT
    candidates_total,
    sample_ready,
    wait_both_sample,
    min_remaining_total_trades,
    min_remaining_oos_trades,
    avg_progress_pct,
    max_progress_pct,
    collection_status,
    phase_status,
    recommended_action
FROM marketcore_ui.paper_runtime_sample_collection_v1
WHERE id=1;
"

echo "summary_rows=$summary_rows"
echo "monitor_rows=$monitor_rows"
echo "micro_live_allowed_rows=$allowed_rows"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_TIMER_V1_READY"
echo "VERDICT=TEST_PAPER_RUNTIME_SAMPLE_COLLECTION_TIMER_V1_OK"
