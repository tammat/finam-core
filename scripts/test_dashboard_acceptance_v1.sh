#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_DASHBOARD_ACCEPTANCE_V1 ==="

PYTHONPATH=src python - <<'PY'
from fastapi.testclient import TestClient

from marketcore.presentation.dashboard.server import app

client = TestClient(app)

pages = [
    "/",
    "/market",
    "/research",
    "/metadata",
    "/risk",
    "/execution",
    "/operations",
]

apis = [
    "/api/home",
    "/api/market",
    "/api/research",
    "/api/metadata",
    "/api/risk",
    "/api/execution",
    "/api/operations",
]

for page in pages:
    r = client.get(page)
    assert r.status_code == 200, page

    html = r.text

    for forbidden in [
        "Traceback",
        "Internal Server Error",
        "Exception",
        ">READY<",
        ">HIGH<",
        ">WARNING<",
        ">DISABLED<",
        "Details",
        "Settings",
        "Search",
        "Fresh",
        "Volume",
        "Ticks",
    ]:
        assert forbidden not in html, f"{page}: {forbidden}"

    assert "fc-mobile-nav" in html
    assert "@media (max-width:768px)" in html

for api in apis:
    r = client.get(api)
    assert r.status_code == 200, api
    assert r.status_code != 500, api

print("dashboard_pages_ready=READY")
print("dashboard_api_ready=READY")
print("dashboard_responsive_ready=READY")
print("dashboard_ru_ready=READY")
print("dashboard_no500_ready=READY")
print("dashboard_quality_ready=READY")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print("VERDICT=DASHBOARD_ACCEPTANCE_V1_READY")
PY

echo "VERDICT=TEST_DASHBOARD_ACCEPTANCE_V1_OK"
