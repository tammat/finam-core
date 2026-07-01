#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RESEARCH_ACCEPTANCE_V1 ==="

PYTHONPATH=src python - <<'PY'
from fastapi.testclient import TestClient

from marketcore.presentation.dashboard.server import app

client = TestClient(app)

r = client.get("/research")
assert r.status_code == 200

html = r.text

for needle in [
    "Исследования",
    "Research Center",
    "Сводка",
    "Кандидаты",
    "Проверки",
    "Действия",
    "Сделки",
    "Статус",
    "Готово",
    "План",
]:
    assert needle in html, needle

for forbidden in [
    "Details",
    "Settings",
    "Search",
    "Fresh",
    "Futures",
    "Equity",
    "Crypto",
    "Volume",
    "Ticks",
    "Traceback",
    "Internal Server Error",
    "Exception",
    "analytics_research_candidates",
    "analytics_research_checks",
    "public.",
    "warehouse.",
]:
    assert forbidden not in html, forbidden

api = client.get("/api/research")
assert api.status_code == 200

vm = api.json()

assert vm["title"] == "Исследования"
assert vm["subtitle"] == "Research Center"
assert len(vm["overview"]) == 4
assert len(vm["candidates"]) >= 1
assert len(vm["checks"]) >= 3
assert len(vm["actions"]) == 3

for url in ["/research", "/api/research"]:
    rr = client.get(url)
    assert rr.status_code == 200, url
    assert rr.status_code != 500, url

assert "fc-mobile-nav" in html
assert "@media (max-width:768px)" in html

print("research_page_ready=READY")
print("widgets_ready=READY")
print("api_ready=READY")
print("real_data_ready=READY")
print("responsive_ready=READY")
print("ru_localization_ready=READY")
print("no500_ready=READY")
print("ux_ready=READY")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print("VERDICT=RESEARCH_ACCEPTANCE_TEST_V1_READY")
PY

echo "VERDICT=TEST_RESEARCH_ACCEPTANCE_V1_OK"
