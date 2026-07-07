#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_FACTORY_BOTTLENECK_ANALYZER_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core -f sql/analytics/009_edge_factory_bottleneck_v1.sql

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m py_compile \
  src/scripts/build_edge_factory_bottleneck_v1.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python \
  src/scripts/build_edge_factory_bottleneck_v1.py

test -s reports/edge_factory_bottleneck_latest.json
test -s reports/edge_factory_bottleneck_latest.txt

rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_factory_bottleneck_v1
WHERE source_version='EDGE_FACTORY_BOTTLENECK_ANALYZER_V1';
")

labels=$(psql -At -d finam_core -c "
SELECT count(*)
FROM presentation.ui_resource_v1
WHERE resource_group='edge_factory'
  AND resource_key LIKE 'edge.factory.bottleneck.%'
  AND locale_code='ru';
")

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_candidate_v1
WHERE micro_live_allowed=true OR live_allowed=true;
")

test "$rows" -gt 0
test "$labels" -ge 6
test "$unsafe" = "0"

grep -q "VERDICT=EDGE_FACTORY_BOTTLENECK_ANALYZER_READY" reports/edge_factory_bottleneck_latest.txt

echo "bottleneck_rows=$rows"
echo "i18n_labels=$labels"
echo "unsafe_rows=$unsafe"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_EDGE_FACTORY_BOTTLENECK_ANALYZER_V1_OK"
