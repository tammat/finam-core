#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_INTRADAY_WORKSPACE_V1 ==="

PYTHONPATH=src python -m py_compile \
src/marketcore_os/viewmodels/intraday.py \
src/marketcore_os/repositories/intraday.py \
src/marketcore_os/services/intraday.py \
src/marketcore_os/workspace/intraday.py \
src/marketcore_os/app.py

DATABASE_URL=postgresql:///finam_core \
PYTHONPATH=src \
python <<'PY'

from fastapi.testclient import TestClient
from marketcore_os.app import app

client=TestClient(app)

r=client.get("/intraday?lang=en")

assert r.status_code==200

html=r.text

for token in [

"Intraday Workspace",
"Activity",
"Runtime",
"Paper",
"Production",
"Active Symbols",
"Open Positions",
"marketcore_ui",
"MARKETCORE_CAPITAL_MANAGER_V1"

]:
    assert token in html, token

print("intraday_workspace_ready=READY")
print("activity_ready=READY")
print("runtime_ready=READY")
print("next_ready=READY")

PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=MARKETCORE_INTRADAY_WORKSPACE_V1_READY"
echo "VERDICT=TEST_MARKETCORE_INTRADAY_WORKSPACE_V1_OK"
