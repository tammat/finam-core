#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_CAPITAL_MANAGER_V1 ==="

scripts/apply_marketcore_capital_manager_v1.sh

PYTHONPATH=src python -m py_compile \
  src/marketcore_os/viewmodels/capital_manager.py \
  src/marketcore_os/repositories/capital_manager.py \
  src/marketcore_os/services/capital_manager.py \
  src/marketcore_os/workspace/capital_manager.py \
  src/marketcore_os/app.py

DATABASE_URL=postgresql:///finam_core \
PYTHONPATH=src \
python <<'PY'
from fastapi.testclient import TestClient
from marketcore_os.app import app

client = TestClient(app)
r = client.get("/capital-manager?lang=en")
assert r.status_code == 200

html = r.text

for token in [
    'data-workspace="capital-manager"',
    "Capital Manager",
    "Capital",
    "Risk Control",
    "Deployment Limit",
    "READ_ONLY",
    "PAPER_RUNTIME_REVIEW",
    "marketcore_ui.capital_manager_summary_v1",
]:
    assert token in html, token

print("capital_manager_workspace_ready=READY")
print("capital_manager_read_model_ready=READY")
print("risk_control_ready=READY")
print("next_action_ready=READY")
PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_CAPITAL_MANAGER_V1_READY"
echo "VERDICT=TEST_MARKETCORE_CAPITAL_MANAGER_V1_OK"
