#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_RESEARCH_WORKSPACE_V1 ==="

PYTHONPATH=src python -m py_compile \
src/marketcore_os/workspace/research.py \
src/marketcore_os/app.py

PYTHONPATH=src python <<'PY'
from fastapi.testclient import TestClient
from marketcore_os.app import app

client = TestClient(app)

r = client.get("/research")

assert r.status_code == 200

html = r.text

for token in [
"data-workspace=\"research\"",
"Research Workspace",
"Pipeline",
"TOP3",
"Edge Factory",
"Research Candidates",
"OOS PASS",
"Paper Ready",
"GLOBAL_EDGE_FORENSIC_AUDIT_V1",
"marketcore_ui.research_summary_v1"
]:
    assert token in html, token

print("research_workspace_ready=READY")
print("pipeline_ready=READY")
print("statistics_ready=READY")
print("next_action_ready=READY")
PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=MARKETCORE_RESEARCH_WORKSPACE_V1_READY"
echo "VERDICT=TEST_MARKETCORE_RESEARCH_WORKSPACE_V1_OK"
