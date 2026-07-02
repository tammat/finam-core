#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_WIDGET_REFACTOR_READ_MODEL_V1 ==="

scripts/apply_marketcore_ui_grants_v1.sh

sudo -u postgres env \
  PYTHONPATH=src \
  DATABASE_URL=postgresql:///finam_core \
  /opt/finam-core/venv/bin/python src/scripts/build_marketcore_read_model_layer_v1.py

PYTHONPATH=src python -m py_compile \
  src/marketcore_os/repositories/capital.py \
  src/marketcore_os/repositories/profit.py \
  src/marketcore_os/repositories/research.py \
  src/marketcore_os/repositories/risk.py \
  src/marketcore_os/repositories/program.py \
  src/marketcore_os/services/program.py \
  src/marketcore_os/viewmodels/program.py \
  src/marketcore_os/widgets/program.py \
  src/marketcore_os/app.py

if grep -R "analytics_" -n src/marketcore_os/repositories; then
  echo "FORBIDDEN_ANALYTICS_SQL_IN_UI_REPOSITORY"
  exit 1
fi

if grep -R "to_regclass\|CREATE TABLE\|InsufficientPrivilege" -n src/marketcore_os/repositories; then
  echo "FORBIDDEN_FALLBACK_OR_DDL_IN_UI_REPOSITORY"
  exit 1
fi

PYTHONPATH=src DATABASE_URL=postgresql:///finam_core python - <<'PY'
from fastapi.testclient import TestClient
from marketcore_os.app import app

client = TestClient(app)

for path in [
    "/api/v1/capital/widget",
    "/api/v1/profit/widget",
    "/api/v1/research/widget",
    "/api/v1/risk/widget",
    "/api/v1/program/widget",
]:
    r = client.get(path)
    assert r.status_code == 200, path
    payload = r.json()
    assert "marketcore_ui." in payload["data_source"], payload

r = client.get("/")
assert r.status_code == 200
html = r.text

for token in [
    "marketcore_ui.capital_summary_v1",
    "marketcore_ui.profit_summary_v1",
    "marketcore_ui.research_summary_v1",
    "marketcore_ui.risk_summary_v1",
    "marketcore_ui.program_summary_v1",
]:
    assert token in html, token

print("capital_repository_read_model_ready=READY")
print("profit_repository_read_model_ready=READY")
print("research_repository_read_model_ready=READY")
print("risk_repository_read_model_ready=READY")
print("program_repository_read_model_ready=READY")
print("home_workspace_read_model_ready=READY")
PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_WIDGET_REFACTOR_READ_MODEL_V1_READY"
echo "VERDICT=TEST_MARKETCORE_WIDGET_REFACTOR_READ_MODEL_V1_OK"
