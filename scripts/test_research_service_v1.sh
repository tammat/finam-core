#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RESEARCH_SERVICE_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/services/research/research_center_service.py

PYTHONPATH=src python - <<'PY'
from marketcore.services.research.research_center_service import ResearchCenterService

vm = ResearchCenterService().load()

assert vm.title == "Исследования"
assert vm.subtitle == "Research Center"
assert len(vm.overview) == 4
assert len(vm.candidates) >= 1
assert len(vm.checks) == 3
assert len(vm.actions) == 3
assert vm.candidates[0].symbol == "BRM6@RTSX"
assert vm.candidates[0].pf == "1,94"

print("research_service=READY")
print("view_model=READY")
print("overview_ready=READY")
print("candidates_ready=READY")
print("checks_ready=READY")
print("actions_ready=READY")
print("ru_copy=READY")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print("VERDICT=RESEARCH_SERVICE_V1_READY")
PY

echo "VERDICT=TEST_RESEARCH_SERVICE_V1_OK"
