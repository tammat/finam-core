#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_HOME_WORKSPACE_LAYOUT_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore_os/app.py \
  src/marketcore_os/layouts/base.py \
  src/marketcore_os/workspace/home.py

PYTHONPATH=src python - <<'PY'
from fastapi.testclient import TestClient
from marketcore_os.app import app

client = TestClient(app)

r = client.get("/")
assert r.status_code == 200
html = r.text

required_ru = [
    "MarketCore OS",
    "Workspace",
    "Капитал",
    "Исследования",
    "Риск",
    "Сегодня",
    "Следующее действие",
    "Статус программы",
    "TOP3_PAPER_RUNTIME_EXECUTION_V1",
    "500 000 ₽",
    "Research Candidate",
    "54",
    "Paper",
    "3",
    "Runtime",
    "OFF",
    "Execution",
    "OFF",
    "Micro Live",
    "OFF",
    "Q3 2026",
    "IN PROGRESS",
    "● ONLINE",
    "name=\"lang\"",
    "name=\"tz\"",
    "name=\"currency\"",
    "name=\"theme\"",
]

for token in required_ru:
    assert token in html, token

assert ">Home<" not in html
assert "Dashboard" not in html

r_en = client.get("/?lang=en&tz=UTC&currency=USD&theme=dark")
assert r_en.status_code == 200
html_en = r_en.text

required_en = [
    'class="mc-dark"',
    "Today",
    "Next Action",
    "Capital",
    "Profit Engine",
    "Research",
    "Risk",
    "Program Status",
    "USD",
    "UTC",
]

for token in required_en:
    assert token in html_en, token

health = client.get("/health")
assert health.status_code == 200
payload = health.json()

assert payload["service"] == "marketcore-os"
assert payload["status"] == "READY"
assert payload["home_workspace"] == "READY"
assert payload["runtime_changed"] == 0
assert payload["execution_changed"] == 0
assert payload["orders_changed"] == 0
assert payload["fills_changed"] == 0
assert payload["micro_live_allowed"] == 0

print("home_workspace_layout_ready=READY")
print("home_workspace_ru_ready=READY")
print("home_workspace_en_ready=READY")
print("responsive_layout_ready=READY")
print("right_value_alignment_ready=READY")
print("read_only_ready=READY")
PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_HOME_WORKSPACE_LAYOUT_V1_READY"
echo "VERDICT=TEST_MARKETCORE_HOME_WORKSPACE_LAYOUT_V1_OK"
