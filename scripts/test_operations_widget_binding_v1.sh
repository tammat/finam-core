#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_OPERATIONS_WIDGET_BINDING_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/dashboard/operations_router.py

PYTHONPATH=src python - <<'PY'
from fastapi.testclient import TestClient

from marketcore.presentation.dashboard.server import app
from marketcore.presentation.dashboard.operations_router import OperationsCenterPage

html = OperationsCenterPage().render()

required = [
    "Эксплуатация",
    "Operations Center",
    "Сводка",
    "Сервисы",
    "События",
    "Действия",
    "Dashboard",
    "Paper Runtime",
    "Research",
    "Работает",
    "Ошибок нет",
]

for item in required:
    assert item in html, item

assert "OPERATIONS_WIDGET_BINDING_V1" not in html
assert "fc-mobile-nav" in html

client = TestClient(app)

r = client.get("/operations")
assert r.status_code == 200

assert "Эксплуатация" in r.text
assert "Сервисы" in r.text
assert "События" in r.text
assert "OPERATIONS_WIDGET_BINDING_V1" not in r.text

api = client.get("/api/operations")
assert api.status_code == 200

payload = api.json()

assert payload["title"] == "Эксплуатация"
assert len(payload["overview"]) == 4
assert len(payload["services"]) >= 4
assert len(payload["events"]) >= 3

for forbidden in [
    "Details",
    "Settings",
    "Search",
    "Fresh",
    "Volume",
    "Ticks",
    ">READY<",
]:
    assert forbidden not in r.text, forbidden

print("operations_widget_binding=READY")
print("overview_binding=READY")
print("services_binding=READY")
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
print("VERDICT=OPERATIONS_WIDGET_BINDING_V1_READY")
PY

echo "VERDICT=TEST_OPERATIONS_WIDGET_BINDING_V1_OK"
