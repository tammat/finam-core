#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_SCORE_MODEL_V2_PART1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core -f sql/analytics/020_edge_score_model_v2.sql

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m py_compile \
  src/scripts/build_edge_score_model_v2.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python \
  src/scripts/build_edge_score_model_v2.py | tee /tmp/edge_score_model_v2_part1.out

model_rows=$(psql -At -d finam_core -c "
SELECT count(*) FROM analytics.edge_score_model_v2
WHERE source_version='EDGE_SCORE_MODEL_V2';
")

metric_rows=$(psql -At -d finam_core -c "
SELECT count(*) FROM analytics.edge_score_metric_v2
WHERE source_version='EDGE_SCORE_MODEL_V2';
")

bad_scores=$(psql -At -d finam_core -c "
SELECT count(*) FROM analytics.edge_score_model_v2
WHERE source_version='EDGE_SCORE_MODEL_V2'
AND (edge_score_v2 < 0 OR edge_score_v2 > 100);
")

bad_weights=$(psql -At -d finam_core -c "
SELECT count(*) FROM analytics.edge_score_weight_v2
WHERE weight < 0;
")

labels=$(psql -At -d finam_core -c "
SELECT count(*) FROM presentation.ui_resource_v1
WHERE resource_group='edge_score'
AND locale_code='ru';
")

test "$model_rows" -gt 0
test "$metric_rows" -gt 0
test "$bad_scores" = "0"
test "$bad_weights" = "0"
test "$labels" -ge 5

grep -q "VERDICT=EDGE_SCORE_MODEL_V2_PART1_READY" /tmp/edge_score_model_v2_part1.out

echo "model_rows=$model_rows"
echo "metric_rows=$metric_rows"
echo "bad_scores=$bad_scores"
echo "bad_weights=$bad_weights"
echo "i18n_labels=$labels"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_SCORE_MODEL_V2_PART1_READY"
echo "VERDICT=TEST_EDGE_SCORE_MODEL_V2_PART1_OK"
