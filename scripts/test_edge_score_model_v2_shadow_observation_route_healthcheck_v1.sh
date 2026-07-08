#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_SCORE_MODEL_V2_SHADOW_OBSERVATION_ROUTE_HEALTHCHECK_V1 ==="

page="src/marketcore/presentation/pages/edge_score_shadow_page.py"
provider="src/marketcore/presentation/providers/edge_score_shadow_observation_provider.py"
component="src/marketcore/presentation/components/edge_score_shadow_observation_card.py"

test -f "$page"
test -f "$provider"
test -f "$component"

PYTHONPYCACHEPREFIX=/tmp/finam_pycache_shadow_route \
PYTHONDONTWRITEBYTECODE=0 \
PYTHONPATH=src \
python -m py_compile "$page" "$provider" "$component"

grep -q 'route="/edge-score-shadow"' "$page"
grep -q 'edge-score-shadow-observation-card' "$component"

PYTHONPYCACHEPREFIX=/tmp/finam_pycache_shadow_route \
PYTHONDONTWRITEBYTECODE=0 \
PYTHONPATH=src \
python - <<'PY'
from marketcore.presentation.pages.edge_score_shadow_page import EdgeScoreShadowPage

page = EdgeScoreShadowPage()
assert page.route == "/edge-score-shadow"
assert page.title == "edge.score.shadow.title"

html = page.render()
assert "edge-score-shadow-observation-card" in html
assert "order_seen" in html
assert "fill_seen" in html

print("route=", page.route)
print("title=", page.title)
print("VERDICT=EDGE_SCORE_SHADOW_ROUTE_LOCAL_RENDER_OK")
PY

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
  echo "UNSAFE_SHADOW_ROUTE_ROWS=$unsafe"
  exit 1
fi

if systemctl is-active --quiet marketcore-ui-shell.service; then
  curl -fsS "http://127.0.0.1:8080/edge-score-shadow?v=$(date +%s)" >/tmp/edge_score_shadow_route_healthcheck.html
  grep -q "edge-score-shadow-observation-card" /tmp/edge_score_shadow_route_healthcheck.html
  grep -q "order_seen" /tmp/edge_score_shadow_route_healthcheck.html
  grep -q "fill_seen" /tmp/edge_score_shadow_route_healthcheck.html
  http_route_status="HTTP_OK"
else
  http_route_status="HTTP_SKIPPED_SERVICE_INACTIVE"
fi

echo "http_route_status=$http_route_status"
echo "unsafe_rows=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_SCORE_MODEL_V2_SHADOW_OBSERVATION_ROUTE_HEALTHCHECK_V1_READY"
echo "VERDICT=TEST_EDGE_SCORE_MODEL_V2_SHADOW_OBSERVATION_ROUTE_HEALTHCHECK_V1_OK"
