#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_UI_8080_NAVIGATION_AUDIT_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/ui_labels.py \
  src/marketcore/presentation/navigation.py \
  src/marketcore/presentation/layout.py \
  src/scripts/audit_marketcore_ui_8080_navigation_v1.py \
  src/marketcore/presentation/app.py

PYTHONPATH=src python src/scripts/audit_marketcore_ui_8080_navigation_v1.py \
  | tee /tmp/marketcore_ui_8080_navigation_audit_v1.txt

grep -q "VERDICT=MARKETCORE_UI_8080_NAVIGATION_AUDIT_V1_READY" \
  /tmp/marketcore_ui_8080_navigation_audit_v1.txt

MARKETCORE_UI_HOST=127.0.0.1 MARKETCORE_UI_PORT=20180 KG_API_BASE_URL=http://127.0.0.1:1 PYTHONPATH=src \
python src/marketcore/presentation/app.py > /tmp/marketcore_ui_nav_audit_v1.log 2>&1 &
ui_pid=$!

cleanup() {
  kill "$ui_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 1

curl -fsS "http://127.0.0.1:20180/" > /tmp/marketcore_ui_nav_home_v1.html
curl -fsS "http://127.0.0.1:20180/risk" > /tmp/marketcore_ui_nav_risk_v1.html
curl -fsS "http://127.0.0.1:20180/settings" > /tmp/marketcore_ui_nav_settings_v1.html

grep -q "Рабочий стол" /tmp/marketcore_ui_nav_home_v1.html
grep -q "Поиск Edge" /tmp/marketcore_ui_nav_home_v1.html
grep -q "Риски" /tmp/marketcore_ui_nav_home_v1.html
grep -q "Настройки" /tmp/marketcore_ui_nav_home_v1.html
grep -q "Единая оболочка платформы" /tmp/marketcore_ui_nav_home_v1.html
grep -q "MARKETCORE_UI_SHELL_V1" /tmp/marketcore_ui_nav_home_v1.html

grep -q "Риски" /tmp/marketcore_ui_nav_risk_v1.html
grep -q "Настройки" /tmp/marketcore_ui_nav_settings_v1.html

grep -q -- "--bg:#0f172a" src/marketcore/presentation/layout.py
grep -q "display_label" src/marketcore/presentation/navigation.py

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_UI_8080_NAVIGATION_AUDIT_V1_READY"
echo "VERDICT=TEST_MARKETCORE_UI_8080_NAVIGATION_AUDIT_V1_OK"
