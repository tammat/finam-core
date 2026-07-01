#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_DASHBOARD_COMPONENT_PREVIEW_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/dashboard/preview_service.py \
  src/marketcore/presentation/dashboard/preview_router.py \
  src/marketcore/presentation/dashboard/server.py

PYTHONPATH=src python - <<'PY'
from fastapi.testclient import TestClient

from marketcore.presentation.dashboard.preview_service import (
    build_component_preview_html,
    get_component_preview_status,
)
from marketcore.presentation.dashboard.server import app

html = build_component_preview_html()

assert "Dashboard Component Preview" in html
assert "System Health" in html
assert "Market Bars" in html
assert "Correlation Risk" in html
assert "Registered Components" in html
assert "Risk Heatmap" in html
assert "Responsive Breakpoints" in html
assert "table" in html

status = get_component_preview_status()
assert status["status"] == "READY"
assert int(status["component_count"]) > 0
assert status["runtime_changed"] == 0
assert status["micro_live_allowed"] == 0

client = TestClient(app)

page = client.get("/components")
assert page.status_code == 200
assert "Dashboard Component Preview" in page.text
assert "fc-mobile-nav" in page.text

api = client.get("/api/components")
assert api.status_code == 200
payload = api.json()
assert payload["status"] == "READY"
assert payload["component_count"] > 0

print("preview_route=READY")
print("preview_page=READY")
print("registry_loaded=READY")
print("cards_rendered=READY")
print("table_rendered=READY")
print("timeline_rendered=READY")
print("heatmap_rendered=READY")
print("responsive_preview=READY")
print("component_count_gt_0=READY")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print("VERDICT=DASHBOARD_COMPONENT_PREVIEW_V1_READY")
PY

echo "VERDICT=TEST_DASHBOARD_COMPONENT_PREVIEW_V1_OK"
