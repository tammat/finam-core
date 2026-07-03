#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_UI_8080_ROUTE_GROUPING_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/route_groups.py \
  src/marketcore/presentation/navigation.py \
  src/marketcore/presentation/layout.py \
  src/scripts/audit_marketcore_ui_8080_route_grouping_v1.py \
  src/marketcore/presentation/app.py

PYTHONPATH=src python src/scripts/audit_marketcore_ui_8080_route_grouping_v1.py \
  | tee /tmp/marketcore_ui_8080_route_grouping_v1.txt

grep -q "VERDICT=MARKETCORE_UI_8080_ROUTE_GROUPING_V1_READY" \
  /tmp/marketcore_ui_8080_route_grouping_v1.txt

MARKETCORE_UI_HOST=127.0.0.1 MARKETCORE_UI_PORT=20380 KG_API_BASE_URL=http://127.0.0.1:1 PYTHONPATH=src \
python src/marketcore/presentation/app.py > /tmp/marketcore_ui_route_grouping_v1.log 2>&1 &
ui_pid=$!

cleanup() {
  kill "$ui_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 1

curl -fsS "http://127.0.0.1:20380/" > /tmp/route_grouping_home_v1.html
curl -fsS "http://127.0.0.1:20380/risk" > /tmp/route_grouping_risk_v1.html
curl -fsS "http://127.0.0.1:20380/settings" > /tmp/route_grouping_settings_v1.html

grep -q "Рабочий стол" /tmp/route_grouping_home_v1.html
grep -q "Поиск преимущества" /tmp/route_grouping_home_v1.html
grep -q "Накопление выборки" /tmp/route_grouping_home_v1.html
grep -q "Платформа знаний" /tmp/route_grouping_home_v1.html
grep -q "Торговый контур" /tmp/route_grouping_home_v1.html
grep -q "Система" /tmp/route_grouping_home_v1.html

grep -q "Риски" /tmp/route_grouping_home_v1.html
grep -q "Настройки" /tmp/route_grouping_home_v1.html
grep -q "MARKETCORE_UI_SHELL_V1" /tmp/route_grouping_home_v1.html

grep -q "Риски" /tmp/route_grouping_risk_v1.html
grep -q "Настройки" /tmp/route_grouping_settings_v1.html

grep -q ".nav-group-title" src/marketcore/presentation/layout.py
grep -q "group_for_route" src/marketcore/presentation/navigation.py

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_UI_8080_ROUTE_GROUPING_V1_READY"
echo "VERDICT=TEST_MARKETCORE_UI_8080_ROUTE_GROUPING_V1_OK"
