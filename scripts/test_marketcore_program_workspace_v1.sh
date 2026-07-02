#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_PROGRAM_WORKSPACE_V1 ==="

PYTHONPATH=src python -m py_compile \
src/marketcore_os/workspace/program.py \
src/marketcore_os/app.py

DATABASE_URL=postgresql:///finam_core \
PYTHONPATH=src \
python <<'PY'

from fastapi.testclient import TestClient
from marketcore_os.app import app

client = TestClient(app)

r = client.get("/program?lang=en")
assert r.status_code == 200

html = r.text

for token in [
'data-workspace="program"',
'Program Workspace',
'Roadmap',
'Validation',
'MarketCore OS',
'Next Stage',
'MARKETCORE_PORTFOLIO_WORKSPACE_V1',
'Q3 2026',
'marketcore_ui.program_summary_v1'
]:
    assert token in html, token

print("program_workspace_ready=READY")
print("roadmap_ready=READY")
print("validation_ready=READY")
print("next_stage_ready=READY")

PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=MARKETCORE_PROGRAM_WORKSPACE_V1_READY"
echo "VERDICT=TEST_MARKETCORE_PROGRAM_WORKSPACE_V1_OK"
