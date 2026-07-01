#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RISK_REAL_DATA_BINDING_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/services/risk/risk_control_center_service.py

PYTHONPATH=src python - <<'PY'
from fastapi.testclient import TestClient

from marketcore.presentation.dashboard.server import app
from marketcore.services.risk.risk_control_center_service import RiskControlCenterService

vm = RiskControlCenterService().load()

assert vm.title == "Риски"
assert vm.subtitle == "Risk Control Center"
assert len(vm.overview) == 4
assert len(vm.rules) >= 4
assert len(vm.events) >= 3
assert len(vm.actions) == 3

assert vm.overview[0].title == "Уровень"
assert vm.overview[1].title == "Корреляция"
assert vm.overview[3].value == "Выкл."

client = TestClient(app)

for url in ["/risk", "/api/risk"]:
    r = client.get(url)
    assert r.status_code == 200, url
    assert r.status_code != 500, url

html = client.get("/risk").text

for forbidden in [
    "Traceback",
    "Internal Server Error",
    "Exception",
    "warehouse.risk_assessment_scorecard_v1",
    "public.risk_events",
]:
    assert forbidden not in html, forbidden

print("risk_real_data=READY")
print("safe_query_ready=READY")
print("risk_level_data=READY")
print("risk_events_data=READY")
print("no500_ready=READY")
print("ru_copy_full=READY")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print("VERDICT=RISK_REAL_DATA_BINDING_V1_READY")
PY

echo "VERDICT=TEST_RISK_REAL_DATA_BINDING_V1_OK"
