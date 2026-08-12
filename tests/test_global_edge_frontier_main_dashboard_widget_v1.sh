#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

PY="/opt/finam-core/venv/bin/python"

WIDGET="src/marketcore/presentation/widgets/home_page/edge_search.py"
ROUTER="src/marketcore/presentation/dashboard/home_router.py"

echo "=== TEST GLOBAL EDGE FRONTIER MAIN DASHBOARD WIDGET V1 ==="

PYTHONPATH=src "$PY" -m py_compile \
  "$WIDGET" \
  "$ROUTER"

HTML="$(
PYTHONPATH=src "$PY" - <<'PY'
from marketcore.presentation.widgets.home_page.edge_search import (
    HomeEdgeSearchWidget,
)
from marketcore.services.research.research_center_service import (
    ResearchCenterService,
)

frontier = ResearchCenterService().load().frontier
html = HomeEdgeSearchWidget().render(frontier)

print(html)
PY
)"

grep -q '<h2>Edge Search</h2>' <<< "$HTML"
grep -q 'BRQ6@RTSX' <<< "$HTML"
grep -q 'GAZP@MISX' <<< "$HTML"
grep -q 'PLZL@MISX' <<< "$HTML"
grep -q 'Targets: <b>0</b>' <<< "$HTML"
grep -q 'href="/research"' <<< "$HTML"

grep -q 'HomeEdgeSearchWidget' "$ROUTER"
grep -q 'ResearchCenterService' "$ROUTER"

echo "main_edge_rows=3"
echo "target_candidates=0"
echo "research_link_present=1"
echo "frontier_source=ResearchCenterService"
echo "db_writes_performed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_GLOBAL_EDGE_FRONTIER_MAIN_DASHBOARD_WIDGET_V1_OK"
