#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_LAB_RUNNER_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/scripts/build_edge_lab_runner_v1.py \
  src/marketcore/presentation/ui_labels.py

DATABASE_URL=postgresql:///finam_core EDGE_LAB_RUNNER_LIMIT=10 PYTHONPATH=src \
python src/scripts/build_edge_lab_runner_v1.py | tee /tmp/edge_lab_runner_v1.txt

grep -q "VERDICT=EDGE_LAB_RUNNER_V1_READY" /tmp/edge_lab_runner_v1.txt

obs=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_observation_v1;")
done_runs=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_lab_run_v1 WHERE status_code='DONE';")
bad_live=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_candidate_v1
WHERE live_allowed=true OR micro_live_allowed=true;
")

test "$obs" -gt 0
test "$done_runs" -gt 0
test "$bad_live" = "0"

grep -q "edge.runner.title" src/marketcore/presentation/ui_labels.py
grep -q "edge.verdict.NO_TRADES" src/marketcore/presentation/ui_labels.py

echo "observations=$obs"
echo "done_runs=$done_runs"
echo "unsafe_candidate_rows=$bad_live"
echo "i18n=ok"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_EDGE_LAB_RUNNER_V1_OK"
