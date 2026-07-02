#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_RISK_WIDGET_REALTIME_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore_os/viewmodels/risk.py \
  src/marketcore_os/repositories/risk.py \
  src/marketcore_os/services/risk.py \
  src/marketcore_os/widgets/risk.py \
  src/marketcore_os/widgets/registry.py \
  src/marketcore_os/workspace/home.py \
  src/marketcore_os/app.py

PYTHONPATH=src python - <<'PY'
from fastapi.testclient import TestClient
from marketcore_os.app import app
from marketcore_os.services.risk import RiskService
from marketcore_os.widgets.registry import widgets_for_workspace

vm = RiskService().get_widget_model()

assert isinstance(vm.runtime_allowed, bool)
assert isinstance(vm.execution_allowed, bool)
assert isinstance(vm.micro_live_allowed, bool)
assert vm.daily_risk_pct >= 0
assert vm.data_source == "POSTGRES"

ids = [w.widget_id for w in widgets_for_workspace("workspace")]
assert "W006_RISK" in ids

client = TestClient(app)

r = client.get("/")
assert r.status_code == 200
html = r.text

for token in [
    'data-widget-id="W006_RISK"',
    "Риск",
    "Runtime",
    "Execution",
    "Micro Live",
    "Daily Risk",
    "POSTGRES",
]:
    assert token in html, token

api = client.get("/api/v1/risk/widget")
assert api.status_code == 200
payload = api.json()

assert payload["data_source"] == "POSTGRES"
assert payload["runtime_changed"] == 0
assert payload["execution_changed"] == 0
assert payload["orders_changed"] == 0
assert payload["fills_changed"] == 0
assert payload["micro_live_allowed_flag"] == 0

print("risk_viewmodel_ready=READY")
print("risk_repository_postgres_ready=READY")
print("risk_service_ready=READY")
print("risk_widget_ready=READY")
print("risk_api_ready=READY")
print("home_workspace_risk_bound_ready=READY")
PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_RISK_WIDGET_REALTIME_V1_READY"
echo "VERDICT=TEST_MARKETCORE_RISK_WIDGET_REALTIME_V1_OK"
