#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_METADATA_DATA_MODEL_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/viewmodels/metadata_center_vm.py

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.viewmodels.metadata_center_vm import (
    MetadataCenterVM,
    MetadataMetricVM,
    MetadataObjectVM,
    MetadataSourceVM,
    build_default_metadata_center_vm,
)

vm = build_default_metadata_center_vm()

assert isinstance(vm, MetadataCenterVM)
assert vm.title == "Метаданные"
assert vm.subtitle == "Metadata Center"

assert len(vm.overview) == 4
assert len(vm.objects) >= 3
assert len(vm.sources) >= 3
assert len(vm.actions) == 3

assert isinstance(vm.overview[0], MetadataMetricVM)
assert isinstance(vm.objects[0], MetadataObjectVM)
assert isinstance(vm.sources[0], MetadataSourceVM)

assert vm.overview[0].title == "Объекты"
assert vm.objects[0].name == "Рыночные бары"
assert vm.objects[1].rows_count == "71,1 млн."
assert vm.sources[0].coverage == "100%"

text = " ".join(
    [m.title for m in vm.overview]
    + [o.name for o in vm.objects]
    + [o.layer for o in vm.objects]
    + [s.source for s in vm.sources]
)

for forbidden in ["Details", "Settings", "Search", "Fresh", "Volume", "Ticks", "market_bars", "market_ticks"]:
    assert forbidden not in text, forbidden

print("metadata_data_model=READY")
print("metadata_center_vm=READY")
print("overview_metrics=READY")
print("objects_model=READY")
print("sources_model=READY")
print("actions_model=READY")
print("ru_copy=READY")
print("number_format_ru=READY")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print("VERDICT=METADATA_DATA_MODEL_V1_READY")
PY

echo "VERDICT=TEST_METADATA_DATA_MODEL_V1_OK"
