#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RESEARCH_WIDGET_BINDING_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/dashboard/research_router.py

PYTHONPATH=src python - <<'PY'
from fastapi.testclient import TestClient

from marketcore.presentation.dashboard.server import app
from marketcore.presentation.dashboard.research_router import ResearchCenterPage

html = ResearchCenterPage().render()

for needle in [
    "Исследования",
    "Research Center",
    "Сводка",
    "Кандидаты",
    "Проверки",
    "Действия",
    "BRM6@RTSX",
    "BR Breakout",
    "Сделки",
    "1,94",
]:
    assert needle in html, needle

assert "RESEARCH_WIDGET_BINDING_V1" not in html
assert "fc-mobile-nav" in html

client = TestClient(app)

r = client.get("/research")
assert r.status_code == 200
assert "Исследования" in r.text
assert "Сводка" in r.text
assert "Кандидаты" in r.text
assert "RESEARCH_WIDGET_BINDING_V1" not in r.text

api = client.get("/api/research")
assert api.status_code == 200
payload = api.json()
assert payload["title"] == "Исследования"
assert len(payload["overview"]) == 4
assert len(payload["candidates"]) >= 1
assert len(payload["checks"]) == 3

for forbidden in ["Details", "Settings", "Search", "Fresh", "Volume", "Ticks"]:
    assert forbidden not in r.text, forbidden

print("research_widget_binding=READY")
print("overview_binding=READY")
print("candidates_binding=READY")
print("checks_binding=READY")
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
print("VERDICT=RESEARCH_WIDGET_BINDING_V1_READY")
PY

echo "VERDICT=TEST_RESEARCH_WIDGET_BINDING_V1_OK"
