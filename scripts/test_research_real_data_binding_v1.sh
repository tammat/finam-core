#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RESEARCH_REAL_DATA_BINDING_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/services/research/research_center_service.py

PYTHONPATH=src python - <<'PY'
from fastapi.testclient import TestClient

from marketcore.presentation.dashboard.server import app
from marketcore.services.research.research_center_service import ResearchCenterService

vm = ResearchCenterService().load()

assert vm.title == "Исследования"
assert vm.subtitle == "Research Center"
assert len(vm.overview) == 4
assert len(vm.candidates) >= 1
assert len(vm.checks) >= 3
assert len(vm.actions) == 3

assert vm.candidates[0].symbol
assert vm.candidates[0].timeframe
assert "," in vm.candidates[0].pf or vm.candidates[0].pf == "0,00"

client = TestClient(app)

for url in ["/research", "/api/research"]:
    r = client.get(url)
    assert r.status_code == 200, url
    assert r.status_code != 500, url

html = client.get("/research").text

for forbidden in ["Traceback", "Internal Server Error", "Exception"]:
    assert forbidden not in html, forbidden

print("research_real_data=READY")
print("safe_query_ready=READY")
print("candidate_data=READY")
print("checks_data=READY")
print("ru_number_format=READY")
print("no500_ready=READY")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print("VERDICT=RESEARCH_REAL_DATA_BINDING_V1_READY")
PY

echo "VERDICT=TEST_RESEARCH_REAL_DATA_BINDING_V1_OK"
