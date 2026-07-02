#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_WIDGET_BINDING_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore_os/widgets/registry.py \
  src/marketcore_os/workspace/home.py \
  src/marketcore_os/app.py

PYTHONPATH=src python - <<'PY'
from fastapi.testclient import TestClient
from marketcore_os.app import app
from marketcore_os.widgets.registry import widgets_for_workspace

widgets = list(widgets_for_workspace("workspace"))
ids = [w.widget_id for w in widgets]

assert "W001_TODAY" in ids
assert "W002_PROGRAM" in ids
assert ids.index("W001_TODAY") < ids.index("W002_PROGRAM")

client = TestClient(app)
r = client.get("/")
assert r.status_code == 200
html = r.text

for token in [
    'data-workspace="home"',
    'data-widget-id="W001_TODAY"',
    'data-widget-id="W002_PROGRAM"',
    "Следующее действие",
    "TOP3_PAPER_RUNTIME_EXECUTION_V1",
    "Статус программы",
    "Q3 2026",
    "MarketCore OS",
    "IN PROGRESS",
]:
    assert token in html, token

assert html.index('data-widget-id="W001_TODAY"') < html.index('data-widget-id="W002_PROGRAM"')
assert "Dashboard" not in html

r_en = client.get("/?lang=en")
assert r_en.status_code == 200
html_en = r_en.text

for token in [
    "Today",
    "Next Action",
    "Program Status",
    "Platform",
    "Research",
]:
    assert token in html_en, token

health = client.get("/health")
payload = health.json()

assert payload["runtime_changed"] == 0
assert payload["execution_changed"] == 0
assert payload["orders_changed"] == 0
assert payload["fills_changed"] == 0
assert payload["micro_live_allowed"] == 0

print("widget_registry_binding_ready=READY")
print("today_widget_bound_ready=READY")
print("program_widget_bound_ready=READY")
print("home_workspace_binding_ready=READY")
print("read_only_ready=READY")
PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_WIDGET_BINDING_V1_READY"
echo "VERDICT=TEST_MARKETCORE_WIDGET_BINDING_V1_OK"
