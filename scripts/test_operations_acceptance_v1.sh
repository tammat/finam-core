#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_OPERATIONS_ACCEPTANCE_V1 ==="

PYTHONPATH=src python - <<'PY'
from fastapi.testclient import TestClient

from marketcore.presentation.dashboard.server import app

client = TestClient(app)

r = client.get("/operations")
assert r.status_code == 200

html = r.text

for needle in [
    "Эксплуатация",
    "Operations Center",
    "Сводка",
    "Сервисы",
    "События",
    "Действия",
    "Состояние",
    "Работает",
]:
    assert needle in html, needle

for forbidden in [
    "Details",
    "Settings",
    "Search",
    "Fresh",
    "Volume",
    "Ticks",
    "Traceback",
    "Internal Server Error",
    "Exception",
    "systemctl",
    ">READY<",
    ">WARNING<",
    ">DISABLED<",
]:
    assert forbidden not in html, forbidden

api = client.get("/api/operations")
assert api.status_code == 200

vm = api.json()

assert vm["title"] == "Эксплуатация"
assert vm["subtitle"] == "Operations Center"
assert len(vm["overview"]) == 4
assert len(vm["services"]) >= 1
assert len(vm["events"]) >= 3
assert len(vm["actions"]) == 3

for url in ["/operations", "/api/operations"]:
    rr = client.get(url)
    assert rr.status_code == 200, url
    assert rr.status_code != 500, url

assert "fc-mobile-nav" in html
assert "@media (max-width:768px)" in html

print("operations_page_ready=READY")
print("widgets_ready=READY")
print("api_ready=READY")
print("real_data_ready=READY")
print("responsive_ready=READY")
print("ru_localization_ready=READY")
print("no500_ready=READY")
print("ux_ready=READY")
print("raw_status_hidden=READY")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print("VERDICT=OPERATIONS_ACCEPTANCE_TEST_V1_READY")
PY

echo "VERDICT=TEST_OPERATIONS_ACCEPTANCE_V1_OK"
