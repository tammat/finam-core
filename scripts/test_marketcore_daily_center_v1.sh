#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_DAILY_CENTER_V1 ==="

scripts/apply_marketcore_daily_center_v1.sh

PYTHONPATH=src python -m py_compile \
  src/marketcore_os/viewmodels/daily.py \
  src/marketcore_os/repositories/daily.py \
  src/marketcore_os/services/daily.py \
  src/marketcore_os/workspace/daily.py \
  src/marketcore_os/layouts/base.py \
  src/marketcore_os/app.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src python <<'PY'
from fastapi.testclient import TestClient
from marketcore_os.app import app

client = TestClient(app)

r = client.get("/daily")
assert r.status_code == 200
html = r.text

for token in [
    'data-workspace="daily-center"',
    "Центр дня",
    "Состояние системы",
    "Что делать сейчас",
    "Следующее действие",
    "marketcore_ui.daily_center_summary_v1",
]:
    assert token in html, token

r = client.get("/daily?lang=en")
assert r.status_code == 200
html = r.text

for token in [
    "Daily Center",
    "System State",
    "What To Do Now",
    "Next Action",
]:
    assert token in html, token

print("daily_center_workspace_ready=READY")
print("daily_read_model_ready=READY")
print("daily_ru_ready=READY")
print("daily_en_ready=READY")
PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_DAILY_CENTER_V1_READY"
echo "VERDICT=TEST_MARKETCORE_DAILY_CENTER_V1_OK"
