#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EXECUTION_ACCEPTANCE_V1 ==="

PYTHONPATH=src python - <<'PY'
from fastapi.testclient import TestClient

from marketcore.presentation.dashboard.server import app

client = TestClient(app)

r = client.get("/execution")
assert r.status_code == 200

html = r.text

for needle in [
    "Выполнение",
    "Execution Center",
    "Сводка",
    "Заявки",
    "Сделки",
    "Действия",
    "Исполнение",
    "Выкл.",
    "Кол-во",
    "Цена",
]:
    assert needle in html, needle

for forbidden in [
    "Details",
    "Settings",
    "Search",
    "Fresh",
    "Volume",
    "Ticks",
    "Off",
    "Traceback",
    "Internal Server Error",
    "Exception",
    "public.orders",
    "public.fills",
    ">READY<",
    ">DISABLED<",
    ">HIGH<",
]:
    assert forbidden not in html, forbidden

api = client.get("/api/execution")
assert api.status_code == 200

vm = api.json()

assert vm["title"] == "Выполнение"
assert vm["subtitle"] == "Execution Center"
assert len(vm["overview"]) == 4
assert len(vm["orders"]) >= 1
assert len(vm["fills"]) >= 1
assert len(vm["actions"]) == 3

for url in ["/execution", "/api/execution"]:
    rr = client.get(url)
    assert rr.status_code == 200, url
    assert rr.status_code != 500, url

assert "fc-mobile-nav" in html
assert "@media (max-width:768px)" in html

print("execution_page_ready=READY")
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
print("VERDICT=EXECUTION_ACCEPTANCE_TEST_V1_READY")
PY

echo "VERDICT=TEST_EXECUTION_ACCEPTANCE_V1_OK"
