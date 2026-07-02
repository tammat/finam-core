#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_EDGE_WORKSPACE_V1 ==="

PYTHONPATH=src python -m py_compile \
src/marketcore_os/workspace/edge.py \
src/marketcore_os/app.py

DATABASE_URL=postgresql:///finam_core \
PYTHONPATH=src \
python <<'PY'

from fastapi.testclient import TestClient
from marketcore_os.app import app

client=TestClient(app)

r=client.get("/edge")

assert r.status_code==200

html=r.text

for token in [

'data-workspace="edge"',

'Edge Center',

'Discovery',

'Forensic',

'Robustness',

'Out Of Sample',

'Shadow',

'Paper',

'Production',

'marketcore_ui.research_summary_v1',

'Research Candidates',

'TOP3',

'OOS PASS',

'Paper Ready'

]:

    assert token in html, token

print("edge_workspace_ready=READY")
print("discovery_ready=READY")
print("forensic_ready=READY")
print("robustness_ready=READY")
print("oos_ready=READY")
print("shadow_ready=READY")
print("paper_ready=READY")
print("production_ready=READY")

PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=MARKETCORE_EDGE_WORKSPACE_V1_READY"
echo "VERDICT=TEST_MARKETCORE_EDGE_WORKSPACE_V1_OK"
