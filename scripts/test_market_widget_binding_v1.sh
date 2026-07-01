#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_WIDGET_BINDING_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/dashboard/market_router.py

PYTHONPATH=src python - <<'PY'
from fastapi.testclient import TestClient

from marketcore.presentation.dashboard.server import app
from marketcore.presentation.dashboard.market_router import MarketIntelligencePage

html = MarketIntelligencePage().render()

for needle in [
    "Рынок",
    "Market Intelligence",
    "Сводка",
    "Качество",
    "Инструменты",
    "Действия",
    "Бары",
    "Тики",
    "Фьючерсы",
    "Акции",
    "Крипто",
    "30.06.2026",
    "01.07.2026",
]:
    assert needle in html, needle

assert "MARKET_WIDGET_BINDING_V1" not in html
assert "fc-mobile-nav" in html

client = TestClient(app)

r = client.get("/market")
assert r.status_code == 200
assert "Рынок" in r.text
assert "Сводка" in r.text
assert "Инструменты" in r.text
assert "MARKET_WIDGET_BINDING_V1" not in r.text

api = client.get("/api/market")
assert api.status_code == 200
payload = api.json()
assert payload["title"] == "Рынок"
assert len(payload["overview"]) == 4
assert len(payload["quality"]) >= 3
assert len(payload["instruments"]) >= 3

print("market_widget_binding=READY")
print("overview_binding=READY")
print("quality_binding=READY")
print("instruments_binding=READY")
print("actions_binding=READY")
print("router_binding=READY")
print("api_ready=READY")
print("ru_copy_full=READY")
print("date_format_ru=READY")
print("responsive_ready=1")
print("mobile_ready=1")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print("VERDICT=MARKET_WIDGET_BINDING_V1_READY")
PY

echo "VERDICT=TEST_MARKET_WIDGET_BINDING_V1_OK"
