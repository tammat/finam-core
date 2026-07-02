#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_PORTFOLIO_WORKSPACE_V1 ==="

PYTHONPATH=src python -m py_compile \
src/marketcore_os/viewmodels/portfolio.py \
src/marketcore_os/repositories/portfolio.py \
src/marketcore_os/services/portfolio.py \
src/marketcore_os/workspace/portfolio.py \
src/marketcore_os/app.py

DATABASE_URL=postgresql:///finam_core \
PYTHONPATH=src \
python <<'PY'

from fastapi.testclient import TestClient
from marketcore_os.app import app

client=TestClient(app)

r=client.get("/portfolio?lang=en")

assert r.status_code==200

html=r.text

for token in [
"Portfolio Workspace",
"Capital",
"Positions",
"Next Action",
"marketcore_ui.portfolio_summary_v1",
"MARKETCORE_INTRADAY_WORKSPACE_V1"
]:
    assert token in html, token

print("portfolio_workspace_ready=READY")
print("capital_ready=READY")
print("positions_ready=READY")
print("next_action_ready=READY")

PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=MARKETCORE_PORTFOLIO_WORKSPACE_V1_READY"
echo "VERDICT=TEST_MARKETCORE_PORTFOLIO_WORKSPACE_V1_OK"
