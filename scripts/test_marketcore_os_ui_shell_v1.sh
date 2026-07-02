#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_OS_UI_SHELL_V1 ==="

PYTHONPATH=src python -m py_compile src/marketcore_os/app.py

PYTHONPATH=src python - <<'PY'
from fastapi.testclient import TestClient
from marketcore_os.app import app

client = TestClient(app)

r = client.get("/")
assert r.status_code == 200
html = r.text

for token in [
    "MarketCore OS",
    'name="lang"',
    'name="tz"',
    'name="currency"',
    'name="theme"',
    "MSK",
    "RUB",
    "Light",
    "Главная",
    "Капитал",
    "Исследования",
    "Настройки",
    "Следующее действие",
]:
    assert token in html, token

assert ">Home<" not in html
assert ">Settings<" not in html

r2 = client.get("/?lang=en&tz=UTC&currency=USD&theme=dark")
assert r2.status_code == 200
html2 = r2.text

for token in [
    'class="mc-dark"',
    "USD",
    "UTC",
    ">Home<",
    ">Capital<",
    ">Research<",
    ">Settings<",
    "Next Action",
]:
    assert token in html2, token

health = client.get("/health")
payload = health.json()

assert payload["service"] == "marketcore-os"
assert payload["status"] == "READY"
assert payload["ui_shell"] == "READY"
assert payload["runtime_changed"] == 0
assert payload["execution_changed"] == 0
assert payload["orders_changed"] == 0
assert payload["fills_changed"] == 0
assert payload["micro_live_allowed"] == 0

print("marketcore_os_shell_ru_ready=READY")
print("marketcore_os_shell_en_ready=READY")
print("language_selector_ready=READY")
print("timezone_selector_ready=READY")
print("currency_selector_ready=READY")
print("theme_selector_ready=READY")
print("read_only_ready=READY")
PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_OS_UI_SHELL_V1_READY"
echo "VERDICT=TEST_MARKETCORE_OS_UI_SHELL_V1_OK"
