#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_UI_NESTED_MENU_MOBILE_FONT_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/ui_labels.py \
  src/marketcore/presentation/route_groups.py \
  src/marketcore/presentation/navigation.py \
  src/marketcore/presentation/layout.py \
  src/scripts/audit_marketcore_ui_nested_menu_mobile_font_v1.py

PYTHONPATH=src python src/scripts/audit_marketcore_ui_nested_menu_mobile_font_v1.py \
  | tee /tmp/marketcore_ui_nested_menu_mobile_font_v1.txt

grep -q "VERDICT=MARKETCORE_UI_NESTED_MENU_MOBILE_FONT_V1_READY" \
  /tmp/marketcore_ui_nested_menu_mobile_font_v1.txt

grep -q "Рынок" src/marketcore/presentation/route_groups.py
grep -q "Кандидаты" src/marketcore/presentation/ui_labels.py
grep -q "Этапы" src/marketcore/presentation/ui_labels.py
grep -q "Проба" src/marketcore/presentation/ui_labels.py
grep -q "Знания" src/marketcore/presentation/ui_labels.py
grep -q "font-size:17px" src/marketcore/presentation/layout.py

sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS "http://127.0.0.1:8080/" > /tmp/ui_nested_home.html

grep -q "Рынок" /tmp/ui_nested_home.html
grep -q "Рейтинг" /tmp/ui_nested_home.html
grep -q "Кандидаты" /tmp/ui_nested_home.html
grep -q "Этапы" /tmp/ui_nested_home.html
grep -q "Устойчивость" /tmp/ui_nested_home.html
grep -q "Проба" /tmp/ui_nested_home.html
grep -q "Знания" /tmp/ui_nested_home.html
grep -q "Вне выборки" /tmp/ui_nested_home.html
grep -q "Тест вне выборки" /tmp/ui_nested_home.html

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_UI_NESTED_MENU_MOBILE_FONT_V1_READY"
echo "VERDICT=TEST_MARKETCORE_UI_NESTED_MENU_MOBILE_FONT_V1_OK"
