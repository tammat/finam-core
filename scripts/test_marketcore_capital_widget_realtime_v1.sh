#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_CAPITAL_WIDGET_REALTIME_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore_os/viewmodels/capital.py \
  src/marketcore_os/repositories/capital.py \
  src/marketcore_os/services/capital.py \
  src/marketcore_os/widgets/capital.py \
  src/marketcore_os/widgets/registry.py \
  src/marketcore_os/app.py

PYTHONPATH=src python - <<'PY'
from fastapi.testclient import TestClient
from marketcore_os.app import app
from marketcore_os.services.capital import CapitalService
from marketcore_os.widgets.registry import widgets_for_workspace

vm = CapitalService().get_widget_model()
assert vm.planned_capital >= 0
assert vm.base_currency == "RUB"
assert vm.display_currency == "RUB"
assert vm.fx_source == "CBR"
assert vm.data_source == "POSTGRES"

ids = [w.widget_id for w in widgets_for_workspace("workspace")]
assert "W003_CAPITAL" in ids

client = TestClient(app)

r = client.get("/")
assert r.status_code == 200
html = r.text

for token in [
    'data-widget-id="W003_CAPITAL"',
    "Капитал",
    "Плановый капитал",
    "Работает",
    "Свободно",
    "Сегодня",
    "POSTGRES",
]:
    assert token in html, token

api = client.get("/api/v1/capital/widget")
assert api.status_code == 200
payload = api.json()

assert payload["base_currency"] == "RUB"
assert payload["display_currency"] == "RUB"
assert payload["fx_source"] == "CBR"
assert payload["data_source"] == "POSTGRES"
assert payload["runtime_changed"] == 0
assert payload["execution_changed"] == 0
assert payload["orders_changed"] == 0
assert payload["fills_changed"] == 0
assert payload["micro_live_allowed"] == 0

print("capital_viewmodel_ready=READY")
print("capital_repository_postgres_ready=READY")
print("capital_service_ready=READY")
print("capital_widget_ready=READY")
print("capital_api_ready=READY")
print("home_workspace_capital_bound_ready=READY")
PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_CAPITAL_WIDGET_REALTIME_V1_READY"
echo "VERDICT=TEST_MARKETCORE_CAPITAL_WIDGET_REALTIME_V1_OK"
