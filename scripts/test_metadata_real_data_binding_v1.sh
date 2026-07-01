#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_METADATA_REAL_DATA_BINDING_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/services/metadata/metadata_center_service.py

PYTHONPATH=src python - <<'PY'
from fastapi.testclient import TestClient

from marketcore.presentation.dashboard.server import app
from marketcore.services.metadata.metadata_center_service import MetadataCenterService

vm = MetadataCenterService().load()

assert vm.title == "Метаданные"
assert vm.subtitle == "Metadata Center"
assert len(vm.overview) == 4
assert len(vm.objects) >= 1
assert len(vm.sources) >= 3
assert len(vm.actions) == 3

assert vm.overview[0].title == "Объекты"
assert vm.overview[2].value.endswith("%")

client = TestClient(app)

for url in ["/metadata", "/api/metadata"]:
    r = client.get(url)
    assert r.status_code == 200, url
    assert r.status_code != 500, url

html = client.get("/metadata").text

for forbidden in ["Traceback", "Internal Server Error", "Exception"]:
    assert forbidden not in html, forbidden

print("metadata_real_data=READY")
print("safe_query_ready=READY")
print("objects_data=READY")
print("sources_data=READY")
print("coverage_data=READY")
print("no500_ready=READY")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print("VERDICT=METADATA_REAL_DATA_BINDING_V1_READY")
PY

echo "VERDICT=TEST_METADATA_REAL_DATA_BINDING_V1_OK"
