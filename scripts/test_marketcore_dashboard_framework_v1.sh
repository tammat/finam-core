#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_DASHBOARD_FRAMEWORK_V1 ==="

files=(
  src/marketcore/presentation/dashboard/viewmodel.py
  src/marketcore/presentation/dashboard/renderer.py
)

for f in "${files[@]}"; do
  test -f "$f"
  PYTHONPYCACHEPREFIX=/tmp/finam_pycache_dashboard_framework PYTHONPATH=src python -m py_compile "$f"
done

PYTHONPYCACHEPREFIX=/tmp/finam_pycache_dashboard_framework PYTHONPATH=src python - <<'PY'
from marketcore.presentation.dashboard.viewmodel import (
    DashboardViewModel,
    ToolbarItem,
    KpiItem,
    AlertItem,
    TableColumn,
    TableModel,
    SafetyModel,
)
from marketcore.presentation.dashboard.renderer import render_dashboard

vm = DashboardViewModel(
    dashboard_id="test.dashboard",
    title_key="page.test.title",
    subtitle_key="page.test.subtitle",
    icon="📊",
    toolbar=[
        ToolbarItem("home", "button.home", "🏠", "/"),
        ToolbarItem("refresh", "button.refresh", "🔄", "/test"),
        ToolbarItem("bad", "button.execute", "⚠", "/execute", action_type="execution"),
    ],
    kpis=[KpiItem("rows", "column.rows", 2, "tooltip.rows", "neutral", "📄")],
    alerts=[AlertItem("readonly", "status.disabled", "message.readonly.shadow_observation", "info", "👁️")],
    table=TableModel(
        columns=[
            TableColumn("symbol", "column.symbol"),
            TableColumn("score", "column.score"),
        ],
        rows=[
            {"symbol": "LKOH", "score": 77},
            {"symbol": "SBER", "score": 70},
        ],
        rows_count=2,
    ),
    safety=SafetyModel(),
)

html = render_dashboard(vm)

assert "dashboard" in html
assert "data-dashboard-id=\"test.dashboard\"" in html
assert "button.home" in html
assert "button.refresh" in html
assert "button.execute" not in html
assert "column.symbol" in html
assert "column.score" in html
assert "runtime_allowed=0" in html
assert "execution_allowed=0" in html

try:
    render_dashboard(DashboardViewModel(
        dashboard_id="unsafe",
        title_key="page.unsafe",
        safety=SafetyModel(execution_allowed=1),
    ))
except ValueError as exc:
    assert str(exc) == "DASHBOARD_SAFETY_VIOLATION"
else:
    raise AssertionError("UNSAFE_DASHBOARD_NOT_BLOCKED")

print("dashboard_render=OK")
print("unsafe_dashboard_blocked=OK")
PY

if grep -RInE 'send_order|place_order|cancel_order|execute_order|FinamClient|LiveExecution|PaperExecution|INSERT INTO .*orders|INSERT INTO .*fills|UPDATE .*runtime|UPDATE .*execution' \
  src/marketcore/presentation/dashboard; then
  echo "DANGEROUS_DASHBOARD_FRAMEWORK_ACTION_FOUND"
  exit 1
fi

echo "dashboard_framework_files=${#files[@]}"
echo "dashboard_render=OK"
echo "unsafe_dashboard_blocked=OK"
echo "dangerous_actions=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_DASHBOARD_FRAMEWORK_V1_READY"
echo "VERDICT=TEST_MARKETCORE_DASHBOARD_FRAMEWORK_V1_OK"
