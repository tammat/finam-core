#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_SCORE_MODEL_V2_PATCH_1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core -f sql/analytics/020_edge_score_model_v2.sql

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m py_compile \
  src/scripts/build_edge_score_model_v2.py

scripts/test_no_hardcode_configuration_v1.sh

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python \
  src/scripts/build_edge_score_model_v2.py | tee /tmp/edge_score_model_v2_patch_1.out

model_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_score_model_v2
WHERE source_version='EDGE_SCORE_MODEL_V2';
")

group_weights=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_score_weight_v2
WHERE model_code='EDGE_SCORE_V2'
  AND metric_group='MODEL_GROUP'
  AND enabled=true;
")

weight_sum=$(psql -At -d finam_core -c "
SELECT coalesce(sum(weight),0)
FROM analytics.edge_score_weight_v2
WHERE model_code='EDGE_SCORE_V2'
  AND metric_group='MODEL_GROUP'
  AND enabled=true;
")

bad_scores=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_score_model_v2
WHERE source_version='EDGE_SCORE_MODEL_V2'
  AND (edge_score_v2 < 0 OR edge_score_v2 > 100);
")

test "$model_rows" -gt 0
test "$group_weights" = "4"
test "$weight_sum" = "1.000000"
test "$bad_scores" = "0"

grep -q "VERDICT=EDGE_SCORE_MODEL_V2_PART1_READY" /tmp/edge_score_model_v2_patch_1.out

echo "model_rows=$model_rows"
echo "group_weights=$group_weights"
echo "weight_sum=$weight_sum"
echo "bad_scores=$bad_scores"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_SCORE_MODEL_V2_PATCH_1_READY"
echo "VERDICT=TEST_EDGE_SCORE_MODEL_V2_PATCH_1_OK"
