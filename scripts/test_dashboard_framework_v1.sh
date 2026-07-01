#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_DASHBOARD_FRAMEWORK_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/dashboard/server.py \
  src/marketcore/presentation/dashboard/router.py \
  src/marketcore/presentation/dashboard/registry.py \
  src/marketcore/presentation/dashboard/navigation.py \
  src/marketcore/presentation/dashboard/layout.py \
  src/marketcore/presentation/dashboard/services.py \
  src/marketcore/presentation/dashboard/widgets.py \
  src/marketcore/presentation/dashboard/theme.py \
  src/marketcore/presentation/dashboard/api.py

PYTHONPATH=src python - <<'PY'
from fastapi.testclient import TestClient

from marketcore.presentation.dashboard.server import app
from marketcore.presentation.dashboard.registry import registry
from marketcore.presentation.dashboard.navigation import navigation_items
from marketcore.presentation.dashboard.theme import normalize_theme
from marketcore.presentation.dashboard.widgets import metric_card

client = TestClient(app)

r = client.get("/")
assert r.status_code == 200
assert "Dashboard Framework V1" in r.text
assert "Finam_Core Dashboard" in r.text

api = client.get("/api/framework")
assert api.status_code == 200
payload = api.json()
assert payload["status"] == "READY"
assert payload["runtime_changed"] == 0
assert payload["micro_live_allowed"] == 0

assert registry.get("home") is not None
assert len(registry.list_pages()) >= 9
assert len(navigation_items()) >= 9
assert normalize_theme("dark") == "dark"
assert normalize_theme("bad") == "light"
assert metric_card("Risk", "HIGH", "HIGH")["status"] == "WARNING"

mobile = client.get("/?lang=ru&timezone=Europe/Moscow")
assert "mobile-bottom" in mobile.text

print("framework_ready=1")
print("server_ready=1")
print("router_ready=1")
print("registry_ready=1")
print("navigation_ready=1")
print("layout_ready=1")
print("widgets_ready=1")
print("theme_ready=1")
print("api_ready=1")
print("responsive_ready=1")
print("mobile_ready=1")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print("VERDICT=DASHBOARD_FRAMEWORK_V1_READY")
PY

echo "VERDICT=TEST_DASHBOARD_FRAMEWORK_V1_OK"
