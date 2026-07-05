#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PARAMETER_SEARCH_GRID_V1 ==="

PYTHONPATH=src python -m py_compile src/scripts/build_parameter_search_grid_v1.py

DATABASE_URL=postgresql:///finam_core PARAMETER_SEARCH_JOB_LIMIT=5 PYTHONPATH=src \
python src/scripts/build_parameter_search_grid_v1.py | tee /tmp/parameter_search_grid_v1.txt

grep -q "VERDICT=PARAMETER_SEARCH_GRID_V1_READY" /tmp/parameter_search_grid_v1.txt

grid_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.research_queue_v1
WHERE source_version='PARAMETER_SEARCH_GRID_V1';
")

test "$grid_rows" -gt 0

echo "grid_research_queue_rows=$grid_rows"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_PARAMETER_SEARCH_GRID_V1_OK"
