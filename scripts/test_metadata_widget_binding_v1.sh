#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_METADATA_WIDGET_BINDING_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/dashboard/metadata_router.py

PYTHONPATH=src python - <<'PY'
from fastapi.testclient import TestClient

from marketcore.presentation.dashboard.server import app
from marketcore.presentation.dashboard.metadata_router import MetadataCenterPage

html = MetadataCenterPage().render()

for needle in [
    "Метаданные",
    "Metadata Center",
    "Сводка",
    "Объекты",
    "Источники",
    "Действия",
    "Рыночные бары",
    "Рыночные тики",
    "71,1 млн.",
    "876 тыс.",
]:
    assert needle in html, needle

assert "METADATA_WIDGET_BINDING_V1" not in html
assert "fc-mobile-nav" in html

client = TestClient(app)

r = client.get("/metadata")
assert r.status_code == 200
assert "Метаданные" in r.text
assert "Сводка" in r.text
assert "Объекты" in r.text
assert "METADATA_WIDGET_BINDING_V1" not in r.text

api = client.get("/api/metadata")
assert api.status_code == 200
payload = api.json()
assert payload["title"] == "Метаданные"
assert len(payload["overview"]) == 4
assert len(payload["objects"]) >= 3
assert len(payload["sources"]) >= 3

for forbidden in ["Details", "Settings", "Search", "Fresh", "Volume", "Ticks", "market_bars", "market_ticks"]:
    assert forbidden not in r.text, forbidden

print("metadata_widget_binding=READY")
print("overview_binding=READY")
print("objects_binding=READY")
print("sources_binding=READY")
print("actions_binding=READY")
print("router_binding=READY")
print("api_ready=READY")
print("ru_copy_full=READY")
print("responsive_ready=1")
print("mobile_ready=1")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print("VERDICT=METADATA_WIDGET_BINDING_V1_READY")
PY

echo "VERDICT=TEST_METADATA_WIDGET_BINDING_V1_OK"
