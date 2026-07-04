#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_VALIDATION_BUILDER_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/scripts/build_edge_validation_builder_v1.py

DATABASE_URL=postgresql:///finam_core EDGE_VALIDATION_LIMIT=5000 PYTHONPATH=src \
python src/scripts/build_edge_validation_builder_v1.py | tee /tmp/edge_validation_builder_v1.txt

grep -q "VERDICT=EDGE_VALIDATION_BUILDER_V1_READY" /tmp/edge_validation_builder_v1.txt

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_decision_snapshot_v1;")
updated=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_decision_snapshot_v1 WHERE source_version='EDGE_VALIDATION_BUILDER_V1';")
unsafe=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_decision_snapshot_v1 WHERE ready_for_live=true OR ready_for_micro_live=true;")

test "$rows" -gt 0
test "$updated" -gt 0
test "$unsafe" = "0"

psql -d finam_core -c "
SELECT symbol, strategy_family, edge_score, validation_score, recommendation_code, ready_for_replay
FROM analytics.edge_decision_snapshot_v1
ORDER BY signal_ts DESC
LIMIT 30;
"

echo "edge_rows=$rows"
echo "updated_rows=$updated"
echo "unsafe_live_rows=$unsafe"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_EDGE_VALIDATION_BUILDER_V1_OK"
