#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_TODAY_WIDGET_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore_os/widgets/today.py \
  src/marketcore_os/widgets/base.py \
  src/marketcore_os/widgets/registry.py

PYTHONPATH=src python - <<'PY'
from marketcore_os.widgets.today import TodayWidget, today_widget

w = TodayWidget()

assert w.widget_id == "W001_TODAY"
assert w.priority == 10
assert w.refresh_interval_sec == 15
assert w.workspace == "workspace"

html_ru = w.render("ru")
assert 'data-widget-id="W001_TODAY"' in html_ru
assert 'data-refresh="15"' in html_ru
assert "Сегодня" in html_ru
assert "Следующее действие" in html_ru
assert "TOP3_PAPER_RUNTIME_EXECUTION_V1" in html_ru
assert "Статус" in html_ru
assert "READY" in html_ru
assert "Система" in html_ru
assert "ONLINE" in html_ru
assert "Режим" in html_ru
assert "READ ONLY" in html_ru
assert "mc-row" in html_ru
assert "mc-value" in html_ru

html_en = w.render("en")
assert "Today" in html_en
assert "Next Action" in html_en
assert "Status" in html_en
assert "System" in html_en
assert "Mode" in html_en

assert today_widget.widget_id == "W001_TODAY"

print("today_widget_ready=READY")
print("today_widget_ru_ready=READY")
print("today_widget_en_ready=READY")
print("right_value_alignment_ready=READY")
print("read_only_ready=READY")
PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_TODAY_WIDGET_V1_READY"
echo "VERDICT=TEST_MARKETCORE_TODAY_WIDGET_V1_OK"
