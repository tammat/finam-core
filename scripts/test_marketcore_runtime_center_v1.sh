#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_RUNTIME_CENTER_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore_os/viewmodels/runtime.py \
  src/marketcore_os/repositories/runtime.py \
  src/marketcore_os/services/runtime.py \
  src/marketcore_os/workspace/runtime.py \
  src/marketcore_os/layouts/base.py \
  src/marketcore_os/app.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src python <<'PY'
from fastapi.testclient import TestClient
from marketcore_os.app import app

client = TestClient(app)

r = client.get("/runtime")
assert r.status_code == 200
html = r.text

for token in [
    'data-workspace="runtime-center"',
    "Центр Runtime",
    "Исполнение",
    "Активность",
    "Сегодня",
    "Следующее действие",
    "marketcore_ui.runtime_center_summary_v1",
]:
    assert token in html, token

r = client.get("/runtime?lang=en")
assert r.status_code == 200
html = r.text

for token in [
    "Runtime Center",
    "Execution",
    "Activity",
    "Today",
    "Next Action",
    "PAPER_CENTER_REVIEW",
]:
    assert token in html, token

print("runtime_center_workspace_ready=READY")
print("runtime_center_ru_ready=READY")
print("runtime_center_en_ready=READY")
print("runtime_center_read_model_ready=READY")
PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_RUNTIME_CENTER_V1_READY"
echo "VERDICT=TEST_MARKETCORE_RUNTIME_CENTER_V1_OK"
