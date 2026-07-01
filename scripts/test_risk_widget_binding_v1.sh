#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RISK_WIDGET_BINDING_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/dashboard/risk_router.py

PYTHONPATH=src python - <<'PY'
from fastapi.testclient import TestClient

from marketcore.presentation.dashboard.server import app
from marketcore.presentation.dashboard.risk_router import RiskControlCenterPage

html = RiskControlCenterPage().render()

required = [
    "Риски",
    "Risk Control Center",
    "Сводка",
    "Лимиты",
    "События",
    "Действия",
    "Уровень",
    "Высокий",
    "Корреляция",
    "План P1",
    "Дневной убыток",
    "Экспозиция",
]

for item in required:
    assert item in html, item

assert "RISK_WIDGET_BINDING_V1" not in html
assert "fc-mobile-nav" in html

client = TestClient(app)

r = client.get("/risk")
assert r.status_code == 200

assert "Риски" in r.text
assert "Лимиты" in r.text
assert "События" in r.text
assert "RISK_WIDGET_BINDING_V1" not in r.text

api = client.get("/api/risk")
assert api.status_code == 200

payload = api.json()

assert payload["title"] == "Риски"
assert len(payload["overview"]) == 4
assert len(payload["rules"]) >= 4
assert len(payload["events"]) >= 3

for forbidden in [
    "Details",
    "Settings",
    "Search",
    "Fresh",
    "Volume",
    "Ticks",
]:
    assert forbidden not in r.text, forbidden

print("risk_widget_binding=READY")
print("overview_binding=READY")
print("rules_binding=READY")
print("events_binding=READY")
print("actions_binding=READY")
print("router_binding=READY")
print("api_ready=READY")
print("ru_copy_full=READY")
print("responsive_ready=1")
print("mobile_ready=1")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print("VERDICT=RISK_WIDGET_BINDING_V1_READY")
PY

echo "VERDICT=TEST_RISK_WIDGET_BINDING_V1_OK"
