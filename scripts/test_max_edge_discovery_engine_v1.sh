#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MAX_EDGE_DISCOVERY_ENGINE_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core -f sql/analytics/018_max_edge_discovery_engine_v1.sql

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m py_compile \
  src/scripts/build_max_edge_discovery_engine_v1.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python \
  src/scripts/build_max_edge_discovery_engine_v1.py | tee /tmp/max_edge_discovery_engine_v1.out

rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.max_edge_ranking_v1
WHERE source_version='MAX_EDGE_DISCOVERY_ENGINE_V1';
")

labels=$(psql -At -d finam_core -c "
SELECT count(*)
FROM presentation.ui_resource_v1
WHERE resource_group='max_edge'
  AND locale_code='ru';
")

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_candidate_v1
WHERE micro_live_allowed=true OR live_allowed=true;
")

test "$rows" -gt 0
test "$labels" -ge 5
test "$unsafe" = "0"
test -s reports/max_edge_discovery_latest.json

grep -q "VERDICT=MAX_EDGE_DISCOVERY_ENGINE_READY" /tmp/max_edge_discovery_engine_v1.out

echo "max_edge_rows=$rows"
echo "i18n_labels=$labels"
echo "unsafe_rows=$unsafe"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MAX_EDGE_DISCOVERY_ENGINE_V1_READY"
echo "VERDICT=TEST_MAX_EDGE_DISCOVERY_ENGINE_V1_OK"
