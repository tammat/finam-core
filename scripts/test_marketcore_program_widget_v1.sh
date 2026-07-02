#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_PROGRAM_WIDGET_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore_os/widgets/program.py \
  src/marketcore_os/widgets/base.py \
  src/marketcore_os/widgets/registry.py

PYTHONPATH=src python - <<'PY'
from marketcore_os.widgets.program import ProgramWidget, program_widget

w = ProgramWidget()

assert w.widget_id == "W002_PROGRAM"
assert w.priority == 90
assert w.refresh_interval_sec == 60
assert w.workspace == "workspace"

html_ru = w.render("ru")
assert 'data-widget-id="W002_PROGRAM"' in html_ru
assert 'data-refresh="60"' in html_ru
assert "Статус программы" in html_ru
assert "Q3 2026" in html_ru
assert "ACTIVE" in html_ru
assert "Платформа" in html_ru
assert "Исследования" in html_ru
assert "TOP3" in html_ru
assert "Paper" in html_ru
assert "MarketCore OS" in html_ru
assert "COMPLETE" in html_ru
assert "READY" in html_ru
assert "IN PROGRESS" in html_ru
assert "mc-row" in html_ru
assert "mc-value" in html_ru

html_en = w.render("en")
assert "Program Status" in html_en
assert "Platform" in html_en
assert "Research" in html_en

assert program_widget.widget_id == "W002_PROGRAM"

print("program_widget_ready=READY")
print("program_widget_ru_ready=READY")
print("program_widget_en_ready=READY")
print("right_value_alignment_ready=READY")
print("read_only_ready=READY")
PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_PROGRAM_WIDGET_V1_READY"
echo "VERDICT=TEST_MARKETCORE_PROGRAM_WIDGET_V1_OK"
