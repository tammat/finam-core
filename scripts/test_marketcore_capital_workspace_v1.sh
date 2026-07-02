#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_CAPITAL_WORKSPACE_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore_os/workspace/capital.py \
  src/marketcore_os/app.py

PYTHONPATH=src python - <<'PY'
from fastapi.testclient import TestClient
from marketcore_os.app import app

client = TestClient(app)

r = client.get("/capital")
assert r.status_code == 200
html = r.text

for token in [
    'data-workspace="capital"',
    "Капитал",
    "Сводка капитала",
    "Плановый капитал",
    "Распределение",
    "FX",
    "Риск капитала",
    "POSTGRES",
    "CBR",
    "RUB",
]:
    assert token in html, token

assert "Dashboard" not in html

r_en = client.get("/capital?lang=en&tz=UTC&currency=RUB&theme=dark")
assert r_en.status_code == 200
html_en = r_en.text

for token in [
    'class="mc-dark"',
    "Capital Summary",
    "Allocation",
    "Capital Risk",
    "Calculations in RUB",
    "Display only",
]:
    assert token in html_en, token

api = client.get("/api/v1/capital/widget")
assert api.status_code == 200
payload = api.json()

assert payload["data_source"] == "POSTGRES"
assert payload["base_currency"] == "RUB"
assert payload["runtime_changed"] == 0
assert payload["execution_changed"] == 0
assert payload["orders_changed"] == 0
assert payload["fills_changed"] == 0
assert payload["micro_live_allowed"] == 0

print("capital_workspace_ready=READY")
print("capital_summary_ready=READY")
print("capital_allocation_ready=READY")
print("capital_fx_ready=READY")
print("capital_risk_ready=READY")
print("read_only_ready=READY")
PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_CAPITAL_WORKSPACE_V1_READY"
echo "VERDICT=TEST_MARKETCORE_CAPITAL_WORKSPACE_V1_OK"
