#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_PROFIT_WIDGET_REALTIME_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore_os/viewmodels/profit.py \
  src/marketcore_os/repositories/profit.py \
  src/marketcore_os/services/profit.py \
  src/marketcore_os/widgets/profit.py \
  src/marketcore_os/widgets/registry.py \
  src/marketcore_os/workspace/home.py \
  src/marketcore_os/app.py

PYTHONPATH=src python - <<'PY'
from fastapi.testclient import TestClient
from marketcore_os.app import app
from marketcore_os.services.profit import ProfitService
from marketcore_os.widgets.registry import widgets_for_workspace

vm = ProfitService().get_widget_model()

assert vm.production_edges >= 0
assert vm.paper_edges >= 0
assert vm.shadow_edges >= 0
assert vm.research_candidates >= 0
assert vm.data_source == "POSTGRES"

ids = [w.widget_id for w in widgets_for_workspace("workspace")]
assert "W004_PROFIT" in ids

client = TestClient(app)

r = client.get("/")
assert r.status_code == 200
html = r.text

for token in [
    'data-widget-id="W004_PROFIT"',
    "Двигатель прибыли",
    "Production",
    "Paper",
    "Paper Status",
    "Shadow",
    "Research Candidate",
    "POSTGRES",
]:
    assert token in html, token

api = client.get("/api/v1/profit/widget")
assert api.status_code == 200
payload = api.json()

assert payload["production_edges"] >= 0
assert payload["paper_edges"] >= 0
assert payload["shadow_edges"] >= 0
assert payload["research_candidates"] >= 0
assert payload["data_source"] == "POSTGRES"
assert payload["runtime_changed"] == 0
assert payload["execution_changed"] == 0
assert payload["orders_changed"] == 0
assert payload["fills_changed"] == 0
assert payload["micro_live_allowed"] == 0

print("profit_viewmodel_ready=READY")
print("profit_repository_postgres_ready=READY")
print("profit_service_ready=READY")
print("profit_widget_ready=READY")
print("profit_api_ready=READY")
print("home_workspace_profit_bound_ready=READY")
PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_PROFIT_WIDGET_REALTIME_V1_READY"
echo "VERDICT=TEST_MARKETCORE_PROFIT_WIDGET_REALTIME_V1_OK"
