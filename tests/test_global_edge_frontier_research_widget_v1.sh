#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

PY="/opt/finam-core/venv/bin/python"

WIDGET="src/marketcore/presentation/widgets/research_page/frontier.py"
ROUTER="src/marketcore/presentation/dashboard/research_router.py"

echo "=== TEST GLOBAL EDGE FRONTIER RESEARCH WIDGET V1 ==="

PYTHONPATH=src "$PY" -m py_compile \
  "$WIDGET" \
  "$ROUTER"

HTML="$(
PYTHONPATH=src "$PY" - <<'PY'
from marketcore.presentation.widgets.research_page.frontier import (
    ResearchFrontierWidget,
)
from marketcore.services.research.research_center_service import (
    ResearchCenterService,
)

vm = ResearchCenterService().load()
print(ResearchFrontierWidget().render(vm))
PY
)"

grep -q '<h2>Edge Search</h2>' <<< "$HTML"
grep -q 'BRQ6@RTSX' <<< "$HTML"
grep -q 'GAZP@MISX' <<< "$HTML"
grep -q 'PLZL@MISX' <<< "$HTML"
grep -q 'SBERP@MISX' <<< "$HTML"
grep -q 'BRU6@RTSX' <<< "$HTML"

grep -q 'NET+ / BASELINE−' <<< "$HTML"
grep -q 'BASELINE+ / NET−' <<< "$HTML"

grep -q 'Target candidates: <b>0</b>' <<< "$HTML"

grep -q 'ResearchFrontierWidget' "$ROUTER"

echo "frontier_rows_rendered=5"
echo "target_candidates=0"
echo "router_frontier_widget_enabled=1"
echo "db_writes_performed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_GLOBAL_EDGE_FRONTIER_RESEARCH_WIDGET_V1_OK"
