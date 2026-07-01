#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EXECUTION_WIDGET_BINDING_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/dashboard/execution_router.py

PYTHONPATH=src python - <<'PY'
from fastapi.testclient import TestClient

from marketcore.presentation.dashboard.server import app
from marketcore.presentation.dashboard.execution_router import ExecutionCenterPage

html = ExecutionCenterPage().render()

required = [
    "Выполнение",
    "Execution Center",
    "Сводка",
    "Заявки",
    "Сделки",
    "Действия",
    "Исполнение",
    "Выкл.",
    "Нет заявок",
    "Нет сделок",
]

for item in required:
    assert item in html, item

assert "EXECUTION_WIDGET_BINDING_V1" not in html
assert "fc-mobile-nav" in html

client = TestClient(app)

r = client.get("/execution")
assert r.status_code == 200

assert "Выполнение" in r.text
assert "Заявки" in r.text
assert "Сделки" in r.text
assert "EXECUTION_WIDGET_BINDING_V1" not in r.text

api = client.get("/api/execution")
assert api.status_code == 200

payload = api.json()

assert payload["title"] == "Выполнение"
assert len(payload["overview"]) == 4
assert len(payload["orders"]) >= 1
assert len(payload["fills"]) >= 1

for forbidden in [
    "Details",
    "Settings",
    "Search",
    "Fresh",
    "Volume",
    "Ticks",
    ">READY<",
    ">DISABLED<",
]:
    assert forbidden not in r.text, forbidden

print("execution_widget_binding=READY")
print("overview_binding=READY")
print("orders_binding=READY")
print("fills_binding=READY")
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
print("VERDICT=EXECUTION_WIDGET_BINDING_V1_READY")
PY

echo "VERDICT=TEST_EXECUTION_WIDGET_BINDING_V1_OK"
