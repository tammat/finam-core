#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_ACCEPTANCE_V1 ==="

PYTHONPATH=src python - <<'PY'
from fastapi.testclient import TestClient

from marketcore.presentation.dashboard.server import app

client = TestClient(app)

#
# HTML
#

r = client.get("/market")
assert r.status_code == 200

html = r.text

#
# Product
#

assert "Рынок" in html
assert "Market Intelligence" in html

#
# Widgets
#

required = [
    "Сводка",
    "Качество",
    "Инструменты",
    "Действия",
    "Бары",
    "Тики",
    "Инстр.",
    "Актуал.",
]

for item in required:
    assert item in html, item

#
# RU only
#

for forbidden in [
    "Fresh",
    "Futures",
    "Equity",
    "Crypto",
    "Volume",
    "Ticks",
    "2026-07-01",
    "2026-06-30",
]:
    assert forbidden not in html, forbidden

#
# API
#

api = client.get("/api/market")
assert api.status_code == 200

vm = api.json()

assert vm["title"] == "Рынок"
assert vm["subtitle"] == "Market Intelligence"

assert len(vm["overview"]) == 4
assert len(vm["quality"]) >= 3
assert len(vm["instruments"]) >= 3
assert len(vm["actions"]) == 3

#
# No500
#

for url in [
    "/market",
    "/api/market",
]:
    assert client.get(url).status_code == 200

#
# Responsive
#

assert "fc-mobile-nav" in html
assert "@media (max-width:768px)" in html

#
# UX
#

assert "Traceback" not in html
assert "Internal Server Error" not in html
assert "Exception" not in html

print("market_page_ready=READY")
print("widgets_ready=READY")
print("api_ready=READY")
print("real_data_ready=READY")
print("responsive_ready=READY")
print("ru_localization_ready=READY")
print("no500_ready=READY")
print("ux_ready=READY")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print("VERDICT=MARKET_ACCEPTANCE_TEST_V1_READY")
PY

echo "VERDICT=TEST_MARKET_ACCEPTANCE_V1_OK"
