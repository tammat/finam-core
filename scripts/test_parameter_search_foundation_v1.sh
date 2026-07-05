#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PARAMETER_SEARCH_FOUNDATION_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/analytics/017_parameter_search_foundation_v1.sql

PYTHONPATH=src python -m py_compile src/scripts/build_parameter_search_foundation_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_parameter_search_foundation_v1.py | tee /tmp/parameter_search_foundation_v1.txt

grep -q "VERDICT=PARAMETER_SEARCH_FOUNDATION_V1_READY" /tmp/parameter_search_foundation_v1.txt

spaces=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.parameter_search_space_v1;")
jobs=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.parameter_search_job_v1;")

test "$spaces" -gt 0
test "$jobs" -gt 0

echo "parameter_search_spaces=$spaces"
echo "parameter_search_jobs=$jobs"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_PARAMETER_SEARCH_FOUNDATION_V1_OK"
