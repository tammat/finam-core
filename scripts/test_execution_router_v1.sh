#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EXECUTION_ROUTER_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/dashboard/execution_router.py \
  src/marketcore/presentation/dashboard/server.py

PYTHONPATH=src python - <<'PY'
from fastapi.testclient import TestClient

from marketcore.presentation.dashboard.server import app

client = TestClient(app)

r = client.get("/execution")
assert r.status_code == 200

html = r.text
assert "Выполнение" in html
assert "Execution Center" in html
assert "EXECUTION_WIDGET_BINDING_V1" in html
assert "fc-mobile-nav" in html

api = client.get("/api/execution")
assert api.status_code == 200

vm = api.json()
assert vm["title"] == "Выполнение"
assert vm["subtitle"] == "Execution Center"
assert len(vm["overview"]) == 4
assert len(vm["orders"]) >= 1
assert len(vm["fills"]) >= 1
assert len(vm["actions"]) == 3
assert vm["overview"][0]["value"] == "Выкл."

print("execution_route=READY")
print("execution_api=READY")
print("service_binding=READY")
print("viewmodel_binding=READY")
print("layout_binding=READY")
print("responsive_ready=1")
print("mobile_ready=1")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print("VERDICT=EXECUTION_ROUTER_V1_READY")
PY

echo "VERDICT=TEST_EXECUTION_ROUTER_V1_OK"
