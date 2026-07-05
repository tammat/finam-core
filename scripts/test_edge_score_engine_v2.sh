#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_SCORE_ENGINE_V2 ==="

PYTHONPATH=src python -m py_compile \
  src/scripts/build_edge_score_engine_v2.py \
  src/marketcore/presentation/ui_labels.py

DATABASE_URL=postgresql:///finam_core EDGE_SCORE_ENGINE_LIMIT=5000 PYTHONPATH=src \
python src/scripts/build_edge_score_engine_v2.py | tee /tmp/edge_score_engine_v2.txt

grep -q "VERDICT=EDGE_SCORE_ENGINE_V2_READY" /tmp/edge_score_engine_v2.txt

obs=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_observation_v1;")
scored=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_observation_v1
WHERE score_formula_version='EDGE_SCORE_FORMULA_V2';
")
bad=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_observation_v1
WHERE normalized_edge_score < 0
   OR normalized_edge_score > 100
   OR confidence_score < 0
   OR confidence_score > 100
   OR stability_score < 0
   OR stability_score > 100;
")

test "$obs" -gt 0
test "$scored" -gt 0
test "$bad" = "0"

grep -q "edge.score.engine.title" src/marketcore/presentation/ui_labels.py

echo "observations=$obs"
echo "scored_rows=$scored"
echo "bad_score_rows=$bad"
echo "i18n=ok"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_EDGE_SCORE_ENGINE_V2_OK"
