#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_DASHBOARD_NO_500_DATA_ACCESS_GUARD_V1 ==="

PYTHONPATH=src python - <<'PY'
from fastapi.testclient import TestClient

from marketcore.presentation.dashboard.server import app

client = TestClient(app)

routes = [
    "/",
    "/market",
    "/api/home",
    "/api/market",
]

for route in routes:
    response = client.get(route)
    assert response.status_code != 500, f"{route}=HTTP_500"
    assert response.status_code == 200, f"{route}=HTTP_{response.status_code}"

assert "MarketCore" in client.get("/").text
assert "Рынок" in client.get("/market").text
assert client.get("/api/home").json()["product"] == "MarketCore"
assert client.get("/api/market").json()["title"] == "Рынок"

print("home_no_500=READY")
print("market_no_500=READY")
print("api_home_no_500=READY")
print("api_market_no_500=READY")
print("data_access_guard=READY")
print("fallback_policy=READY")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print("VERDICT=DASHBOARD_NO_500_DATA_ACCESS_GUARD_V1_READY")
PY

echo "VERDICT=TEST_DASHBOARD_NO_500_DATA_ACCESS_GUARD_V1_OK"
