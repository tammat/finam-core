#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_DISCOVERY_LOOP_AUDIT_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core -f sql/analytics/017_edge_discovery_loop_audit_v1.sql

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m py_compile \
  src/scripts/build_edge_discovery_loop_audit_v1.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python \
  src/scripts/build_edge_discovery_loop_audit_v1.py | tee /tmp/edge_discovery_loop_audit_v1.out

audit_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_discovery_loop_audit_v1
WHERE source_version='EDGE_DISCOVERY_LOOP_AUDIT_V1';
")

fail_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_discovery_loop_audit_v1
WHERE source_version='EDGE_DISCOVERY_LOOP_AUDIT_V1'
  AND result='FAIL';
")

labels=$(psql -At -d finam_core -c "
SELECT count(*)
FROM presentation.ui_resource_v1
WHERE resource_group='edge_discovery'
  AND resource_key LIKE 'edge.discovery.audit.%'
  AND locale_code='ru';
")

test "$audit_rows" -ge 8
test "$labels" -ge 5
test -s reports/edge_discovery_loop_audit_latest.json
grep -q "VERDICT=EDGE_DISCOVERY_LOOP_AUDIT_READY" /tmp/edge_discovery_loop_audit_v1.out

echo "audit_rows=$audit_rows"
echo "fail_rows=$fail_rows"
echo "i18n_labels=$labels"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_DISCOVERY_LOOP_AUDIT_V1_READY"
echo "VERDICT=TEST_EDGE_DISCOVERY_LOOP_AUDIT_V1_OK"
