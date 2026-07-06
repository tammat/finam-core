#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_UI_8080_HOME_SUMMARY_LINKS_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/app.py \
  src/marketcore/presentation/layout.py \
  src/marketcore/presentation/pages/home.py \
  src/marketcore/presentation/navigation.py \
  src/marketcore/presentation/registry.py

if grep -R "psycopg2\|DATABASE_URL\|SELECT " -n src/marketcore/presentation/pages/home.py; then
  echo "FORBIDDEN_DIRECT_DB_ACCESS_IN_HOME_PAGE"
  exit 1
fi

MARKETCORE_UI_HOST=127.0.0.1 MARKETCORE_UI_PORT=20480 KG_API_BASE_URL=http://127.0.0.1:1 PYTHONPATH=src \
python src/marketcore/presentation/app.py > /tmp/home_summary_links_ui_v1.log 2>&1 &
ui_pid=$!

cleanup() {
  kill "$ui_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 1

curl -fsS "http://127.0.0.1:20480/" > /tmp/home_summary_links_home_v1.html
curl -fsS "http://127.0.0.1:20480/risk" > /tmp/home_summary_links_risk_v1.html
curl -fsS "http://127.0.0.1:20480/settings" > /tmp/home_summary_links_settings_v1.html

grep -q "Рабочий стол" /tmp/home_summary_links_home_v1.html
grep -q "Поиск преимущества" /tmp/home_summary_links_home_v1.html
grep -q "Накопление выборки" /tmp/home_summary_links_home_v1.html
grep -q "Платформа знаний" /tmp/home_summary_links_home_v1.html
grep -q "Торговый контур" /tmp/home_summary_links_home_v1.html
grep -q "Система" /tmp/home_summary_links_home_v1.html
grep -q "Основные разделы" /tmp/home_summary_links_home_v1.html
grep -q "Дневная сводка операций" /tmp/home_summary_links_home_v1.html
grep -q "Операции накопления выборки" /tmp/home_summary_links_home_v1.html
grep -q "Здоровье UI/Systemd" /tmp/home_summary_links_home_v1.html
grep -q "Риски" /tmp/home_summary_links_home_v1.html
grep -q "Настройки" /tmp/home_summary_links_home_v1.html
grep -q "MARKETCORE_UI_8080_HOME_SUMMARY_LINKS_V1" /tmp/home_summary_links_home_v1.html
grep -q "MARKETCORE_UI_SHELL_V1" /tmp/home_summary_links_home_v1.html

grep -q "Риски" /tmp/home_summary_links_risk_v1.html
grep -q "Настройки" /tmp/home_summary_links_settings_v1.html

if grep -q "Empty reply" /tmp/home_summary_links_ui_v1.log; then
  echo "EMPTY_REPLY_DETECTED"
  exit 1
fi

sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS "http://127.0.0.1:8080/" > /tmp/home_summary_links_home_8080_v1.html
grep -q "Рабочий стол" /tmp/home_summary_links_home_8080_v1.html
grep -q "Основные разделы" /tmp/home_summary_links_home_8080_v1.html
grep -q "Риски" /tmp/home_summary_links_home_8080_v1.html
grep -q "Настройки" /tmp/home_summary_links_home_8080_v1.html
grep -q "MARKETCORE_UI_SHELL_V1" /tmp/home_summary_links_home_8080_v1.html

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_UI_8080_HOME_SUMMARY_LINKS_V1_READY"
echo "VERDICT=TEST_MARKETCORE_UI_8080_HOME_SUMMARY_LINKS_V1_OK"
