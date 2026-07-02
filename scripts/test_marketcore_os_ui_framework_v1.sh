#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_OS_UI_FRAMEWORK_V1 ==="

PYTHONPATH=src python -m py_compile src/marketcore_os/app.py

PYTHONPATH=src python - <<'PY'
from fastapi.testclient import TestClient
from marketcore_os.app import app

client = TestClient(app)

r = client.get("/")
assert r.status_code == 200
html = r.text

required_ru = [
    "MarketCore OS",
    "Капитал",
    "Двигатель прибыли",
    "Research Candidate",
    "TOP3 Validation",
    "Paper Runtime",
    "Риск",
    "Следующее действие",
    "TOP3_PAPER_RUNTIME_EXECUTION_V1",
    "☰",
    "RUB",
    "Europe/Moscow",
    "Главная",
    "Исследования",
    "Интрадей",
    "Портфель",
    "Программа",
    "Настройки",
]

for token in required_ru:
    assert token in html, token

assert "Capital</h3>" not in html
assert ">Home<" not in html
assert ">Research<" not in html
assert ">Settings<" not in html

assert "500 000 ₽" in html
assert "OFF" in html
assert "READY" in html

r_en = client.get("/?lang=en")
assert r_en.status_code == 200
html_en = r_en.text

required_en = [
    "Capital",
    "Profit Engine",
    "Risk",
    "Next Action",
    ">Home<",
    ">Research<",
    ">Settings<",
]

for token in required_en:
    assert token in html_en, token

health = client.get("/health")
assert health.status_code == 200
payload = health.json()

assert payload["service"] == "marketcore-os"
assert payload["status"] == "READY"
assert payload["runtime_changed"] == 0
assert payload["execution_changed"] == 0
assert payload["orders_changed"] == 0
assert payload["fills_changed"] == 0
assert payload["micro_live_allowed"] == 0

print("marketcore_os_home_ru_ready=READY")
print("marketcore_os_home_en_ready=READY")
print("marketcore_os_health_ready=READY")
print("read_only_ready=READY")
PY

grep -q "Description=MarketCore OS UI on 8090" deploy/systemd/marketcore-os.service
grep -q -- "--port 8090" deploy/systemd/marketcore-os.service

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_OS_UI_FRAMEWORK_V1_READY"
echo "VERDICT=TEST_MARKETCORE_OS_UI_FRAMEWORK_V1_OK"
