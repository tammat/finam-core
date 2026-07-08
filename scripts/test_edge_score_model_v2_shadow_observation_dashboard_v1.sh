#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_SCORE_MODEL_V2_SHADOW_OBSERVATION_DASHBOARD_V1 ==="

PYTHONPYCACHEPREFIX=/tmp/finam_pycache_shadow_dashboard \
PYTHONDONTWRITEBYTECODE=0 \
PYTHONPATH=src \
python -m py_compile \
  src/marketcore/presentation/providers/edge_score_shadow_observation_provider.py \
  src/marketcore/presentation/components/edge_score_shadow_observation_card.py

PYTHONPYCACHEPREFIX=/tmp/finam_pycache_shadow_dashboard \
PYTHONDONTWRITEBYTECODE=0 \
PYTHONPATH=src \
python - <<'PY'
from marketcore.presentation.providers.edge_score_shadow_observation_provider import EdgeScoreShadowObservationProvider
from marketcore.presentation.components.edge_score_shadow_observation_card import render_edge_score_shadow_observation_card

vm = EdgeScoreShadowObservationProvider().load(limit=20)
assert vm["runtime_allowed"] == 0
assert vm["execution_allowed"] == 0
assert vm["micro_live_allowed"] == 0
assert vm["rows_total"] >= 1, "NO_SHADOW_OBSERVATION_ROWS"

html = render_edge_score_shadow_observation_card(vm)
assert "edge-score-shadow-observation-card" in html
assert "order_seen" in html
assert "fill_seen" in html

print("provider_rows=", vm["rows_total"])
print("VERDICT=EDGE_SCORE_SHADOW_OBSERVATION_RENDER_LOCAL_OK")
PY

if grep -RInE 'send_order|place_order|cancel_order|execute_order|FinamClient|ExecutionEngine|PaperExecution|LiveExecution|INSERT INTO .*orders|INSERT INTO .*fills|UPDATE .*runtime|UPDATE .*execution' \
  src/marketcore/presentation/providers/edge_score_shadow_observation_provider.py \
  src/marketcore/presentation/components/edge_score_shadow_observation_card.py; then
  echo "EXECUTION_COUPLING_FOUND"
  exit 1
fi

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_score_model_v2_shadow_observation_v1
WHERE source_version='EDGE_SCORE_MODEL_V2_SHADOW_OBSERVATION_COLLECTOR_V1'
  AND (
      runtime_allowed <> 0
   OR execution_allowed <> 0
   OR micro_live_allowed <> 0
   OR order_seen <> 0
   OR fill_seen <> 0
  );
")

if [ "$unsafe" != "0" ]; then
  echo "UNSAFE_SHADOW_ROWS=$unsafe"
  exit 1
fi

echo "unsafe_rows=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_SCORE_MODEL_V2_SHADOW_OBSERVATION_DASHBOARD_V1_READY"
echo "VERDICT=TEST_EDGE_SCORE_MODEL_V2_SHADOW_OBSERVATION_DASHBOARD_V1_OK"
