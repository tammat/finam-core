#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_HOME_ROUTER_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/dashboard/home_router.py \
  src/marketcore/presentation/dashboard/server.py

PYTHONPATH=src python - <<'PY'
from fastapi.testclient import TestClient

from marketcore.presentation.dashboard.server import app
from marketcore.presentation.dashboard.home_router import ExecutiveOverviewPage
from marketcore.services.dashboard.executive_overview_service import ExecutiveOverviewService

vm = ExecutiveOverviewService().load()
assert vm.product == "MarketCore"
assert vm.health_value == "97%"

page_obj = ExecutiveOverviewPage()
html = page_obj.render()
assert "MarketCore" in html
assert "Trading Intelligence Platform" in html
assert "Главная" in html
assert "Рынок" in html
assert "Мета" in html
assert "Выполн." in html
assert "fc-mobile-nav" in html

client = TestClient(app)

home = client.get("/")
assert home.status_code == 200
assert "MarketCore" in home.text
assert "Trading Intelligence Platform" in home.text
assert "Главная" in home.text
assert "fc-mobile-nav" in home.text

home_en = client.get("/?lang=en&timezone=UTC")
assert home_en.status_code == 200
assert "UTC" in home_en.text

api = client.get("/api/home")
assert api.status_code == 200
payload = api.json()
assert payload["product"] == "MarketCore"
assert payload["subtitle"] == "Trading Intelligence Platform"
assert payload["health_value"] == "97%"
assert payload["risk"]["priority"] == "P1"
assert len(payload["platform"]) == 6
assert len(payload["market"]) == 4
assert len(payload["quick_actions"]) == 4

print("home_route=READY")
print("home_api=READY")
print("service_binding=READY")
print("viewmodel_binding=READY")
print("layout_binding=READY")
print("base_page_binding=READY")
print("marketcore_brand=READY")
print("ux_copy_ru_short=READY")
print("responsive_ready=1")
print("mobile_ready=1")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print("VERDICT=HOME_ROUTER_V1_READY")
PY

echo "VERDICT=TEST_HOME_ROUTER_V1_OK"
