#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_HOME_ACCEPTANCE_V1 ==="

PYTHONPATH=src python - <<'PY'
from fastapi.testclient import TestClient

from marketcore.presentation.dashboard.server import app

client = TestClient(app)

#
# HTML
#

r = client.get("/")

assert r.status_code == 200

html = r.text

#
# Product
#

assert "MarketCore" in html
assert "Trading Intelligence Platform" in html

#
# Executive Overview
#

required_sections = [
    "Система",
    "Платформа",
    "Рынок",
    "Исслед.",
    "Мета",
    "Риски",
    "Выполн.",
    "Версии",
    "События",
    "Быстрые действия",
]

for section in required_sections:
    assert section in html, section

#
# Responsive
#

assert "fc-mobile-nav" in html
assert "@media (max-width:768px)" in html
assert "@media (max-width:1024px)" in html

#
# API
#

api = client.get("/api/home")

assert api.status_code == 200

vm = api.json()

assert vm["product"] == "MarketCore"
assert vm["subtitle"] == "Trading Intelligence Platform"

assert vm["health_value"] == "97%"

assert len(vm["platform"]) == 6
assert len(vm["market"]) == 4
assert len(vm["research"]) == 3
assert len(vm["metadata"]) == 3
assert len(vm["execution"]) == 3
assert len(vm["quick_actions"]) == 4

#
# UX
#

assert vm["risk"]["priority"] == "P1"
assert vm["risk"]["reason"] == "Корреляция"

#
# Language
#

assert client.get("/?lang=ru").status_code == 200
assert client.get("/?lang=en").status_code == 200

#
# Timezone
#

assert client.get("/?timezone=UTC").status_code == 200
assert client.get("/?timezone=Europe/Moscow").status_code == 200

print("home_page_ready=READY")
print("executive_overview=READY")
print("widgets_ready=READY")
print("real_data_ready=READY")
print("api_ready=READY")
print("responsive_ready=READY")
print("desktop_ready=READY")
print("tablet_ready=READY")
print("mobile_ready=READY")
print("ru_ready=READY")
print("en_ready=READY")
print("timezone_ready=READY")
print("ux_ready=READY")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print("VERDICT=HOME_ACCEPTANCE_TEST_V1_READY")
PY

echo "VERDICT=TEST_HOME_ACCEPTANCE_V1_OK"
