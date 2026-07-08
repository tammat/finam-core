#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_SCORE_MODEL_V2_SHADOW_OBSERVATION_FINAL_AUDIT ==="

files=(
  src/scripts/build_edge_score_model_v2.py
  src/scripts/build_edge_score_model_v2_reconciliation.py
  src/scripts/build_edge_score_model_v2_explain.py
  src/scripts/build_edge_score_model_v2_shadow_observation_collector.py
  src/marketcore/presentation/providers/max_edge_provider.py
  src/marketcore/presentation/providers/edge_score_shadow_observation_provider.py
  src/marketcore/presentation/components/max_edge_card.py
  src/marketcore/presentation/components/edge_score_shadow_observation_card.py
  src/marketcore/presentation/pages/max_edge_page.py
  src/marketcore/presentation/pages/edge_score_shadow_page.py
)

for f in "${files[@]}"; do
  test -f "$f"
  PYTHONPYCACHEPREFIX=/tmp/finam_pycache_shadow_final PYTHONPATH=src python -m py_compile "$f"
done

edge_score_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_score_model_v2;")
reconciliation_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_score_model_v2_reconciliation;")
explain_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_score_model_v2_explain;")
shadow_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_score_model_v2_shadow_observation_v1;")

test "$edge_score_rows" -gt 0
test "$reconciliation_rows" -gt 0
test "$explain_rows" -gt 0
test "$shadow_rows" -gt 0

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_score_model_v2_shadow_observation_v1
WHERE runtime_allowed<>0
   OR execution_allowed<>0
   OR micro_live_allowed<>0
   OR order_seen<>0
   OR fill_seen<>0;
")

test "$unsafe" = "0"

curl -fsS "http://127.0.0.1:8080/max-edge?v=$(date +%s)" >/tmp/max_edge_shadow_final.html
curl -fsS "http://127.0.0.1:8080/edge-score-shadow?v=$(date +%s)" >/tmp/edge_score_shadow_final.html

grep -q "edge-score-explain-card" /tmp/max_edge_shadow_final.html
grep -q "edge-score-shadow-observation-card" /tmp/edge_score_shadow_final.html

echo "edge_score_rows=$edge_score_rows"
echo "reconciliation_rows=$reconciliation_rows"
echo "explain_rows=$explain_rows"
echo "shadow_rows=$shadow_rows"
echo "unsafe_rows=0"
echo "runtime_allowed=0"
echo "execution_allowed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_SCORE_MODEL_V2_SHADOW_OBSERVATION_FINAL_AUDIT_READY"
echo "VERDICT=TEST_EDGE_SCORE_MODEL_V2_SHADOW_OBSERVATION_FINAL_AUDIT_OK"
