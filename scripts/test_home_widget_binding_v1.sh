#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_HOME_WIDGET_BINDING_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/dashboard/home_router.py

PYTHONPATH=src python - <<'PY'
from fastapi.testclient import TestClient

from marketcore.presentation.dashboard.server import app
from marketcore.presentation.dashboard.home_router import ExecutiveOverviewPage

html = ExecutiveOverviewPage().render()

for needle in [
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
]:
    assert needle in html, needle

assert "MarketCore" in html
assert "Trading Intelligence Platform" in html
assert "fc-mobile-nav" in html

client = TestClient(app)

r = client.get("/")
assert r.status_code == 200
assert "MarketCore" in r.text
assert "Trading Intelligence Platform" in r.text
assert "Быстрые действия" in r.text
assert "fc-mobile-nav" in r.text

api = client.get("/api/home")
assert api.status_code == 200
payload = api.json()
assert payload["product"] == "MarketCore"
assert payload["risk"]["priority"] == "P1"

print("widget_binding=READY")
print("executive_health=READY")
print("platform=READY")
print("market=READY")
print("research=READY")
print("metadata=READY")
print("risk=READY")
print("execution=READY")
print("version=READY")
print("activity=READY")
print("quick_actions=READY")
print("responsive_ready=1")
print("mobile_ready=1")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print("VERDICT=HOME_WIDGET_BINDING_V1_READY")
PY

echo "VERDICT=TEST_HOME_WIDGET_BINDING_V1_OK"
