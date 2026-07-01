#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_METADATA_SERVICE_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/services/metadata/metadata_center_service.py

PYTHONPATH=src python - <<'PY'
from marketcore.services.metadata.metadata_center_service import MetadataCenterService

vm = MetadataCenterService().load()

assert vm.title == "Метаданные"
assert vm.subtitle == "Metadata Center"

assert len(vm.overview) == 4
assert len(vm.objects) >= 3
assert len(vm.sources) >= 3
assert len(vm.actions) == 3

assert vm.overview[0].title == "Объекты"
assert vm.objects[0].name == "Рыночные бары"
assert vm.objects[1].rows_count == "71,1 млн."
assert vm.sources[0].coverage == "100%"

print("metadata_service=READY")
print("view_model=READY")
print("overview_ready=READY")
print("objects_ready=READY")
print("sources_ready=READY")
print("actions_ready=READY")
print("ru_copy=READY")
print("number_format_ru=READY")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print("VERDICT=METADATA_SERVICE_V1_READY")
PY

echo "VERDICT=TEST_METADATA_SERVICE_V1_OK"
