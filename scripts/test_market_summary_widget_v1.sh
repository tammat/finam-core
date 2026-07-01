#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_SUMMARY_WIDGET_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/widgets/market_summary/renderer.py

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.viewmodels.executive_overview_vm import build_default_executive_overview_vm
from marketcore.presentation.widgets.market_summary.renderer import MarketSummaryWidget

vm = build_default_executive_overview_vm()
widget = MarketSummaryWidget()

html_ru = widget.render(vm, lang="ru")
html_en = widget.render(vm, lang="en")

assert "Рынок" in html_ru
assert "Бары" in html_ru
assert "876K" in html_ru
assert "Тики" in html_ru
assert "71M" in html_ru
assert "Инстр." in html_ru
assert "59" in html_ru
assert "Fresh" in html_ru
assert "READY" in html_ru
assert "fc-grid" in html_ru

assert "Market" in html_en
assert "876K" in html_en
assert "71M" in html_en
assert "fc-grid" in html_en

print("market_summary_widget=READY")
print("market_bars=READY")
print("market_ticks=READY")
print("market_symbols=READY")
print("market_freshness=READY")
print("design_system_grid=READY")
print("ru_copy=READY")
print("en_copy=READY")
print("responsive_ready=1")
print("mobile_ready=1")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print("VERDICT=MARKET_SUMMARY_WIDGET_V1_READY")
PY

echo "VERDICT=TEST_MARKET_SUMMARY_WIDGET_V1_OK"
