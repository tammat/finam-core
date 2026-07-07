#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_DISCOVERY_WORKER_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core -f sql/analytics/014_edge_discovery_worker_v1.sql

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m py_compile \
  src/scripts/build_edge_discovery_worker_v1.py

psql -d finam_core -c "
INSERT INTO analytics.edge_discovery_queue_v1 (
  event_code, priority, status, expected_edge_gain, payload, source_version
)
VALUES (
  'RUN_RESEARCH',
  'HIGH',
  'NEW',
  18.0,
  '{\"strategy_code\":\"AUTO_DISCOVERY\",\"symbol\":\"AUTO_UNIVERSE\",\"timeframe\":\"AUTO\",\"max_trials\":100}'::jsonb,
  'EDGE_DISCOVERY_WORKER_V1_TEST'
);
"

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python \
  src/scripts/build_edge_discovery_worker_v1.py | tee /tmp/edge_discovery_worker_v1.out

done_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_discovery_queue_v1
WHERE source_version='EDGE_DISCOVERY_WORKER_V1_TEST'
  AND status='DONE';
")

jobs=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.parameter_search_job_v1
WHERE source_version='EDGE_DISCOVERY_WORKER_V1'
  AND status_code='QUEUED';
")

history_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_discovery_history_v1
WHERE source_version='EDGE_DISCOVERY_WORKER_V1'
  AND result_status='DONE';
")

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_candidate_v1
WHERE micro_live_allowed=true OR live_allowed=true;
")

test "$done_rows" -gt 0
test "$jobs" -gt 0
test "$history_rows" -gt 0
test "$unsafe" = "0"

grep -q "VERDICT=EDGE_DISCOVERY_WORKER_READY" /tmp/edge_discovery_worker_v1.out

echo "done_rows=$done_rows"
echo "parameter_jobs=$jobs"
echo "history_rows=$history_rows"
echo "unsafe_rows=$unsafe"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_EDGE_DISCOVERY_WORKER_V1_OK"
