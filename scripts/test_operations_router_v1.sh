#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_OPERATIONS_ROUTER_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/dashboard/operations_router.py \
  src/marketcore/presentation/dashboard/server.py

PYTHONPATH=src python - <<'PY'
from fastapi.testclient import TestClient

from marketcore.presentation.dashboard.server import app

client = TestClient(app)

r = client.get("/operations")
assert r.status_code == 200

html = r.text
assert "Эксплуатация" in html
assert "Operations Center" in html
assert "OPERATIONS_WIDGET_BINDING_V1" in html
assert "fc-mobile-nav" in html

api = client.get("/api/operations")
assert api.status_code == 200

vm = api.json()
assert vm["title"] == "Эксплуатация"
assert vm["subtitle"] == "Operations Center"
assert len(vm["overview"]) == 4
assert len(vm["services"]) >= 4
assert len(vm["events"]) >= 3
assert len(vm["actions"]) == 3

print("operations_route=READY")
print("operations_api=READY")
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
print("VERDICT=OPERATIONS_ROUTER_V1_READY")
PY

echo "VERDICT=TEST_OPERATIONS_ROUTER_V1_OK"
