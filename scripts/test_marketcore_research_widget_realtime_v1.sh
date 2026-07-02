#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_RESEARCH_WIDGET_REALTIME_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore_os/viewmodels/research.py \
  src/marketcore_os/repositories/research.py \
  src/marketcore_os/services/research.py \
  src/marketcore_os/widgets/research.py \
  src/marketcore_os/widgets/registry.py \
  src/marketcore_os/workspace/home.py \
  src/marketcore_os/app.py

PYTHONPATH=src python - <<'PY'
from fastapi.testclient import TestClient
from marketcore_os.app import app
from marketcore_os.services.research import ResearchService
from marketcore_os.widgets.registry import widgets_for_workspace

vm = ResearchService().get_widget_model()

assert vm.research_candidates >= 0
assert vm.oos_pass >= 0
assert vm.paper_ready >= 0
assert vm.data_source == "POSTGRES"

ids = [w.widget_id for w in widgets_for_workspace("workspace")]
assert "W005_RESEARCH" in ids

client = TestClient(app)

r = client.get("/")
assert r.status_code == 200
html = r.text

for token in [
    'data-widget-id="W005_RESEARCH"',
    "Исследования",
    "Pipeline",
    "TOP3 Validation",
    "Edge Factory",
    "Research Candidate",
    "OOS PASS",
    "Paper Ready",
    "POSTGRES",
]:
    assert token in html, token

api = client.get("/api/v1/research/widget")
assert api.status_code == 200
payload = api.json()

assert payload["research_candidates"] >= 0
assert payload["oos_pass"] >= 0
assert payload["paper_ready"] >= 0
assert payload["data_source"] == "POSTGRES"
assert payload["runtime_changed"] == 0
assert payload["execution_changed"] == 0
assert payload["orders_changed"] == 0
assert payload["fills_changed"] == 0
assert payload["micro_live_allowed"] == 0

print("research_viewmodel_ready=READY")
print("research_repository_postgres_ready=READY")
print("research_service_ready=READY")
print("research_widget_ready=READY")
print("research_api_ready=READY")
print("home_workspace_research_bound_ready=READY")
PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_RESEARCH_WIDGET_REALTIME_V1_READY"
echo "VERDICT=TEST_MARKETCORE_RESEARCH_WIDGET_REALTIME_V1_OK"
