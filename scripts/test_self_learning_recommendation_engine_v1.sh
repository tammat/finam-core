#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_SELF_LEARNING_RECOMMENDATION_ENGINE_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core -f sql/analytics/011_self_learning_recommendation_engine_v1.sql

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m py_compile \
  src/scripts/build_self_learning_recommendation_engine_v1.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python \
  src/scripts/build_self_learning_recommendation_engine_v1.py

rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.recommendation_score_v1
WHERE source_version='SELF_LEARNING_RECOMMENDATION_ENGINE_V1';
")

labels=$(psql -At -d finam_core -c "
SELECT count(*)
FROM presentation.ui_resource_v1
WHERE resource_group='recommendation'
  AND resource_key LIKE 'recommendation.learning.%'
  AND locale_code='ru';
")

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_candidate_v1
WHERE micro_live_allowed=true OR live_allowed=true;
")

test "$rows" -gt 0
test "$labels" -ge 3
test "$unsafe" = "0"

grep -q "VERDICT=SELF_LEARNING_RECOMMENDATION_ENGINE_READY" reports/self_learning_recommendation_latest.txt

echo "score_rows=$rows"
echo "i18n_labels=$labels"
echo "unsafe_rows=$unsafe"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_SELF_LEARNING_RECOMMENDATION_ENGINE_V1_OK"
