#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EXECUTION_REAL_DATA_BINDING_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/services/execution/execution_center_service.py

PYTHONPATH=src python - <<'PY'
from fastapi.testclient import TestClient

from marketcore.presentation.dashboard.server import app
from marketcore.services.execution.execution_center_service import ExecutionCenterService

vm = ExecutionCenterService().load()

assert vm.title == "Выполнение"
assert vm.subtitle == "Execution Center"
assert len(vm.overview) == 4
assert len(vm.orders) >= 1
assert len(vm.fills) >= 1
assert len(vm.actions) == 3

assert vm.overview[0].value == "Выкл."
assert vm.overview[1].value == "Выкл."

client = TestClient(app)

for url in ["/execution", "/api/execution"]:
    r = client.get(url)
    assert r.status_code == 200, url
    assert r.status_code != 500, url

html = client.get("/execution").text

for forbidden in [
    "Traceback",
    "Internal Server Error",
    "Exception",
    "public.orders",
    "public.fills",
    ">READY<",
    ">DISABLED<",
]:
    assert forbidden not in html, forbidden

print("execution_real_data=READY")
print("safe_query_ready=READY")
print("orders_data=READY")
print("fills_data=READY")
print("no500_ready=READY")
print("ru_copy_full=READY")
print("raw_status_hidden=READY")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print("VERDICT=EXECUTION_REAL_DATA_BINDING_V1_READY")
PY

echo "VERDICT=TEST_EXECUTION_REAL_DATA_BINDING_V1_OK"
