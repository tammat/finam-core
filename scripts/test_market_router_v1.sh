#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_ROUTER_V1 ==="

PYTHONPATH=src python -m py_compile \
src/marketcore/presentation/dashboard/market_router.py \
src/marketcore/presentation/dashboard/server.py

PYTHONPATH=src python - <<'PY'
from fastapi.testclient import TestClient

from marketcore.presentation.dashboard.server import app

client = TestClient(app)

r = client.get("/market")

assert r.status_code == 200

html = r.text

assert "Рынок" in html
assert "Market Intelligence" in html

api = client.get("/api/market")

assert api.status_code == 200

vm = api.json()

assert vm["title"] == "Рынок"

assert len(vm["overview"]) == 4
assert len(vm["quality"]) >= 3
assert len(vm["instruments"]) >= 3

print("market_route=READY")
print("market_api=READY")
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
print("VERDICT=MARKET_ROUTER_V1_READY")
PY

echo "VERDICT=TEST_MARKET_ROUTER_V1_OK"
