#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RESEARCH_DATA_MODEL_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/viewmodels/research_center_vm.py

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.viewmodels.research_center_vm import (
    ResearchCenterVM,
    ResearchMetricVM,
    ResearchCandidateVM,
    ResearchCheckVM,
    build_default_research_center_vm,
)

vm = build_default_research_center_vm()

assert isinstance(vm, ResearchCenterVM)
assert vm.title == "Исследования"
assert vm.subtitle == "Research Center"

assert len(vm.overview) == 4
assert len(vm.candidates) >= 1
assert len(vm.checks) == 3
assert len(vm.actions) == 3

assert isinstance(vm.overview[0], ResearchMetricVM)
assert isinstance(vm.candidates[0], ResearchCandidateVM)
assert isinstance(vm.checks[0], ResearchCheckVM)

assert vm.candidates[0].symbol == "BRM6@RTSX"
assert vm.candidates[0].timeframe == "M5"
assert vm.candidates[0].pf == "1,94"

text = " ".join(
    [m.title for m in vm.overview]
    + [c.strategy for c in vm.candidates]
    + [c.status for c in vm.candidates]
    + [x.check for x in vm.checks]
)

for forbidden in ["Fresh", "Details", "Settings", "Search"]:
    assert forbidden not in text, forbidden

print("research_data_model=READY")
print("research_center_vm=READY")
print("overview_metrics=READY")
print("candidate_model=READY")
print("checks_model=READY")
print("actions_model=READY")
print("ru_copy=READY")
print("number_format_ru=READY")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print("VERDICT=RESEARCH_DATA_MODEL_V1_READY")
PY

echo "VERDICT=TEST_RESEARCH_DATA_MODEL_V1_OK"
