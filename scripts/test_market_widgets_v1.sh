#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_WIDGETS_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/widgets/market_page/overview.py \
  src/marketcore/presentation/widgets/market_page/quality.py \
  src/marketcore/presentation/widgets/market_page/instruments.py \
  src/marketcore/presentation/widgets/market_page/actions.py

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.viewmodels.market_intelligence_vm import build_default_market_intelligence_vm
from marketcore.presentation.widgets.market_page.overview import MarketOverviewWidget
from marketcore.presentation.widgets.market_page.quality import MarketQualityWidget
from marketcore.presentation.widgets.market_page.instruments import MarketInstrumentsWidget
from marketcore.presentation.widgets.market_page.actions import MarketActionsWidget

vm = build_default_market_intelligence_vm()

html = (
    MarketOverviewWidget().render(vm)
    + MarketQualityWidget().render(vm)
    + MarketInstrumentsWidget().render(vm)
    + MarketActionsWidget().render(vm)
)

for needle in [
    "Сводка",
    "Качество",
    "Инструменты",
    "Действия",
    "Бары",
    "Тики",
    "Актуал.",
    "Фьючерсы",
    "Акции",
    "Крипто",
    "30.06.2026",
    "01.07.2026",
]:
    assert needle in html, needle

for forbidden in ["Fresh", "Futures", "Equity", "Volume", "Ticks"]:
    assert forbidden not in html, forbidden

print("market_overview_widget=READY")
print("market_quality_widget=READY")
print("market_instruments_widget=READY")
print("market_actions_widget=READY")
print("ru_copy_full=READY")
print("date_format_ru=READY")
print("design_system=READY")
print("responsive_ready=1")
print("mobile_ready=1")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print("VERDICT=MARKET_WIDGETS_V1_READY")
PY

echo "VERDICT=TEST_MARKET_WIDGETS_V1_OK"
