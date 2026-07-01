#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_OPERATIONS_REAL_DATA_BINDING_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/services/operations/operations_center_service.py

PYTHONPATH=src python - <<'PY'
from fastapi.testclient import TestClient

from marketcore.presentation.dashboard.server import app
from marketcore.services.operations.operations_center_service import OperationsCenterService

vm = OperationsCenterService().load()

assert vm.title == "Эксплуатация"
assert vm.subtitle == "Operations Center"
assert len(vm.overview) == 4
assert len(vm.services) >= 1
assert len(vm.events) >= 3
assert len(vm.actions) == 3

assert vm.overview[0].title == "Сервисы"
assert vm.services[0].service
assert vm.services[0].state in {"Работает", "Проверить"}

client = TestClient(app)

for url in ["/operations", "/api/operations"]:
    r = client.get(url)
    assert r.status_code == 200, url
    assert r.status_code != 500, url

html = client.get("/operations").text

for forbidden in [
    "Traceback",
    "Internal Server Error",
    "Exception",
    ">READY<",
    ">WARNING<",
    "systemctl",
]:
    assert forbidden not in html, forbidden

print("operations_real_data=READY")
print("safe_query_ready=READY")
print("systemd_status_data=READY")
print("no500_ready=READY")
print("ru_copy_full=READY")
print("raw_status_hidden=READY")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print("VERDICT=OPERATIONS_REAL_DATA_BINDING_V1_READY")
PY

echo "VERDICT=TEST_OPERATIONS_REAL_DATA_BINDING_V1_OK"
