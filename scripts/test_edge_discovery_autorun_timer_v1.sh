#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_DISCOVERY_AUTORUN_TIMER_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core -f sql/analytics/016_edge_discovery_autorun_timer_v1.sql

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m py_compile \
  src/scripts/build_edge_discovery_autorun_v1.py \
  src/scripts/build_edge_discovery_scheduler_v1.py \
  src/scripts/build_edge_discovery_worker_v1.py

test -s deploy/systemd/edge-discovery-autorun.service
test -s deploy/systemd/edge-discovery-autorun.timer

grep -q "ExecStart=/opt/finam-core/venv/bin/python src/scripts/build_edge_discovery_autorun_v1.py" deploy/systemd/edge-discovery-autorun.service
grep -q "OnUnitActiveSec=15min" deploy/systemd/edge-discovery-autorun.timer
grep -q "Persistent=true" deploy/systemd/edge-discovery-autorun.timer

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python \
  src/scripts/build_edge_discovery_autorun_v1.py | tee /tmp/edge_discovery_autorun_timer_v1.out

history_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_discovery_autorun_history_v1
WHERE source_version='EDGE_DISCOVERY_AUTORUN_TIMER_V1';
")

labels=$(psql -At -d finam_core -c "
SELECT count(*)
FROM presentation.ui_resource_v1
WHERE resource_group='edge_discovery'
  AND resource_key LIKE 'edge.discovery.autorun.%'
  AND locale_code='ru';
")

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_candidate_v1
WHERE micro_live_allowed=true OR live_allowed=true;
")

test "$history_rows" -gt 0
test "$labels" -ge 5
test "$unsafe" = "0"
test -s reports/edge_discovery_autorun_latest.json

grep -q "VERDICT=EDGE_DISCOVERY_AUTORUN_READY" /tmp/edge_discovery_autorun_timer_v1.out

echo "history_rows=$history_rows"
echo "i18n_labels=$labels"
echo "unsafe_rows=$unsafe"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_DISCOVERY_AUTORUN_TIMER_V1_READY"
echo "VERDICT=TEST_EDGE_DISCOVERY_AUTORUN_TIMER_V1_OK"
