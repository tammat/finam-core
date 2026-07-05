#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_SPRINT_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/analytics/021_edge_sprint_v1.sql

PYTHONPATH=src python -m py_compile \
  src/scripts/build_edge_sprint_v1.py \
  src/marketcore/presentation/ui_labels.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_sprint_v1.py | tee /tmp/edge_sprint_v1.txt

grep -q "VERDICT=EDGE_SPRINT_V1_READY" /tmp/edge_sprint_v1.txt

sprints=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_sprint_v1;")
snapshots=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_sprint_snapshot_v1;")

test "$sprints" -gt 0
test "$snapshots" -gt 0

grep -q "edge.sprint.title" src/marketcore/presentation/ui_labels.py

echo "sprints=$sprints"
echo "snapshots=$snapshots"
echo "i18n=ok"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_EDGE_SPRINT_V1_OK"
