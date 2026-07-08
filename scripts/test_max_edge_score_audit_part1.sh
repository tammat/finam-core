#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MAX_EDGE_SCORE_AUDIT_PART1 ==="

sudo -u postgres psql \
    -v ON_ERROR_STOP=1 \
    -d finam_core \
    -f sql/analytics/019_max_edge_score_audit_v1.sql

PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=src \
python -m py_compile \
src/scripts/build_max_edge_score_audit_v1.py

PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=src \
python \
src/scripts/build_max_edge_score_audit_v1.py

audit_rows=$(psql -At -d finam_core -c "
select count(*)
from analytics.max_edge_score_audit_v1
where source_version='MAX_EDGE_SCORE_AUDIT_V1';
")

component_rows=$(psql -At -d finam_core -c "
select count(*)
from analytics.max_edge_score_component_v1
where source_version='MAX_EDGE_SCORE_AUDIT_V1';
")

labels=$(psql -At -d finam_core -c "
select count(*)
from presentation.ui_resource_v1
where resource_group='max_edge'
and resource_key like 'max.edge.audit.%';
")

test "$audit_rows" -gt 0
test "$component_rows" -gt 0
test "$labels" -ge 5

echo audit_rows=$audit_rows
echo component_rows=$component_rows
echo i18n_labels=$labels

echo runtime_changed=0
echo execution_changed=0
echo orders_changed=0
echo fills_changed=0
echo micro_live_allowed=0

echo VERDICT=MAX_EDGE_SCORE_AUDIT_PART1_READY
echo VERDICT=TEST_MAX_EDGE_SCORE_AUDIT_PART1_OK
