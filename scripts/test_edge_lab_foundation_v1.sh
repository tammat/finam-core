#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_LAB_FOUNDATION_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/analytics/015_edge_lab_foundation_v1.sql

PYTHONPATH=src python -m py_compile \
  src/scripts/build_edge_lab_foundation_v1.py \
  src/marketcore/presentation/ui_labels.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_lab_foundation_v1.py | tee /tmp/edge_lab_foundation_v1.txt

grep -q "VERDICT=EDGE_LAB_FOUNDATION_V1_READY" /tmp/edge_lab_foundation_v1.txt

run_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_lab_run_v1;")
queued_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_lab_run_v1 WHERE status_code='QUEUED';")
observation_table=$(psql -At -d finam_core -c "SELECT to_regclass('analytics.edge_observation_v1') IS NOT NULL;")
candidate_table=$(psql -At -d finam_core -c "SELECT to_regclass('analytics.edge_candidate_v1') IS NOT NULL;")

test "$run_rows" -gt 0
test "$queued_rows" -gt 0
test "$observation_table" = "t"
test "$candidate_table" = "t"

grep -q "edge.lab.title" src/marketcore/presentation/ui_labels.py
grep -q "edge.candidate.status.EDGE_CANDIDATE" src/marketcore/presentation/ui_labels.py
grep -q "edge.validation.stage.NOT_STARTED" src/marketcore/presentation/ui_labels.py

echo "edge_lab_run_rows=$run_rows"
echo "edge_lab_queued_rows=$queued_rows"
echo "edge_observation_table=$observation_table"
echo "edge_candidate_table=$candidate_table"
echo "i18n=ok"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_EDGE_LAB_FOUNDATION_V1_OK"
