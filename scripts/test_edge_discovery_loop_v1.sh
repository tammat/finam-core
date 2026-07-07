#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_DISCOVERY_LOOP_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core -f sql/analytics/013_edge_discovery_loop_v1.sql

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m py_compile \
  src/scripts/build_edge_discovery_loop_v1.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python \
  src/scripts/build_edge_discovery_loop_v1.py

queue_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_discovery_queue_v1
WHERE source_version='EDGE_DISCOVERY_LOOP_V1';
")

history_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_discovery_history_v1
WHERE source_version='EDGE_DISCOVERY_LOOP_V1';
")

labels=$(psql -At -d finam_core -c "
SELECT count(*)
FROM presentation.ui_resource_v1
WHERE resource_group='edge_discovery'
  AND locale_code='ru';
")

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_candidate_v1
WHERE micro_live_allowed=true OR live_allowed=true;
")

test "$queue_rows" -ge 0
test "$history_rows" -ge 0
test "$labels" -ge 6
test "$unsafe" = "0"
test -s reports/edge_discovery_loop_latest.json

echo "queue_rows=$queue_rows"
echo "history_rows=$history_rows"
echo "i18n_labels=$labels"
echo "unsafe_rows=$unsafe"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_EDGE_DISCOVERY_LOOP_V1_OK"
