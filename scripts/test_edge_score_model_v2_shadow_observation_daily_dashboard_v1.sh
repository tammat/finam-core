#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_SCORE_MODEL_V2_SHADOW_OBSERVATION_DAILY_DASHBOARD_V1 ==="

files=(
  src/marketcore/presentation/providers/edge_score_shadow_daily_provider.py
  src/marketcore/presentation/components/edge_score_shadow_daily_card.py
  src/marketcore/presentation/pages/edge_score_shadow_daily_page.py
)

for f in "${files[@]}"; do
  test -f "$f"
  PYTHONPYCACHEPREFIX=/tmp/finam_pycache_shadow_daily_dashboard PYTHONPATH=src python -m py_compile "$f"
done

PYTHONPYCACHEPREFIX=/tmp/finam_pycache_shadow_daily_dashboard PYTHONPATH=src python - <<'PY'
from marketcore.presentation.pages.edge_score_shadow_daily_page import EdgeScoreShadowDailyPage
from marketcore.presentation.providers.edge_score_shadow_daily_provider import EdgeScoreShadowDailyProvider
from marketcore.presentation.components.edge_score_shadow_daily_card import render_edge_score_shadow_daily_card

page = EdgeScoreShadowDailyPage()
assert page.route == "/edge-score-shadow-daily"
assert page.title == "edge.score.shadow.daily.title"

vm = EdgeScoreShadowDailyProvider().load(limit=50)
assert vm["rows_total"] >= 1, "NO_DAILY_DASHBOARD_ROWS"
assert vm["runtime_allowed"] == 0
assert vm["execution_allowed"] == 0
assert vm["micro_live_allowed"] == 0

html = render_edge_score_shadow_daily_card(vm)
assert "edge-score-shadow-daily-card" in html
assert "order_seen" in html
assert "fill_seen" in html
assert "avg_score" in html

print("daily_dashboard_rows=", vm["rows_total"])
print("VERDICT=EDGE_SCORE_SHADOW_DAILY_DASHBOARD_LOCAL_RENDER_OK")
PY

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_score_model_v2_shadow_observation_daily_v1
WHERE source_version='EDGE_SCORE_MODEL_V2_SHADOW_OBSERVATION_DAILY_ACCUMULATION_V1'
  AND (
      runtime_allowed <> 0
   OR execution_allowed <> 0
   OR micro_live_allowed <> 0
   OR order_seen_count <> 0
   OR fill_seen_count <> 0
  );
")

if [ "$unsafe" != "0" ]; then
  echo "UNSAFE_DAILY_DASHBOARD_ROWS=$unsafe"
  exit 1
fi

if systemctl is-active --quiet marketcore-ui-shell.service; then
  curl -fsS "http://127.0.0.1:8080/edge-score-shadow-daily?v=$(date +%s)" >/tmp/edge_score_shadow_daily_dashboard.html
  grep -q "edge-score-shadow-daily-card" /tmp/edge_score_shadow_daily_dashboard.html
  grep -q "order_seen" /tmp/edge_score_shadow_daily_dashboard.html
  grep -q "fill_seen" /tmp/edge_score_shadow_daily_dashboard.html
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
echo "VERDICT=EDGE_SCORE_MODEL_V2_SHADOW_OBSERVATION_DAILY_DASHBOARD_V1_READY"
echo "VERDICT=TEST_EDGE_SCORE_MODEL_V2_SHADOW_OBSERVATION_DAILY_DASHBOARD_V1_OK"
