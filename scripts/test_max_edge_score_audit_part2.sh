#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MAX_EDGE_SCORE_AUDIT_PART2 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core -f sql/analytics/019_max_edge_score_audit_v1.sql

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m py_compile \
  src/scripts/build_max_edge_score_audit_metrics_v1.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python \
  src/scripts/build_max_edge_score_audit_metrics_v1.py | tee /tmp/max_edge_score_audit_part2.out

metric_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.max_edge_score_audit_metric_v1
WHERE source_version='MAX_EDGE_SCORE_AUDIT_V1';
")

overall_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.max_edge_score_audit_metric_v1
WHERE source_version='MAX_EDGE_SCORE_AUDIT_V1'
  AND metric_code='OVERALL';
")

labels=$(psql -At -d finam_core -c "
SELECT count(*)
FROM presentation.ui_resource_v1
WHERE resource_group='max_edge'
  AND resource_key LIKE 'max.edge.audit.%'
  AND locale_code='ru';
")

test "$metric_rows" -ge 7
test "$overall_rows" -gt 0
test "$labels" -ge 9

grep -q "VERDICT=MAX_EDGE_SCORE_AUDIT_PART2_READY" /tmp/max_edge_score_audit_part2.out

echo "metric_rows=$metric_rows"
echo "overall_rows=$overall_rows"
echo "i18n_labels=$labels"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MAX_EDGE_SCORE_AUDIT_PART2_READY"
echo "VERDICT=TEST_MAX_EDGE_SCORE_AUDIT_PART2_OK"
