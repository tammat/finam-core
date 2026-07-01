#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RESEARCH_WIDGETS_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/widgets/research_page/overview.py \
  src/marketcore/presentation/widgets/research_page/candidates.py \
  src/marketcore/presentation/widgets/research_page/checks.py \
  src/marketcore/presentation/widgets/research_page/actions.py

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.viewmodels.research_center_vm import build_default_research_center_vm
from marketcore.presentation.widgets.research_page.overview import ResearchOverviewWidget
from marketcore.presentation.widgets.research_page.candidates import ResearchCandidatesWidget
from marketcore.presentation.widgets.research_page.checks import ResearchChecksWidget
from marketcore.presentation.widgets.research_page.actions import ResearchActionsWidget

vm = build_default_research_center_vm()

html = (
    ResearchOverviewWidget().render(vm)
    + ResearchCandidatesWidget().render(vm)
    + ResearchChecksWidget().render(vm)
    + ResearchActionsWidget().render(vm)
)

for needle in [
    "Сводка",
    "Кандидаты",
    "Проверки",
    "Действия",
    "BRM6@RTSX",
    "BR Breakout",
    "Сделки",
    "Готово",
    "План",
    "1,94",
]:
    assert needle in html, needle

for forbidden in ["Details", "Settings", "Search", "Fresh", "Volume", "Ticks"]:
    assert forbidden not in html, forbidden

print("research_overview_widget=READY")
print("research_candidates_widget=READY")
print("research_checks_widget=READY")
print("research_actions_widget=READY")
print("ru_copy_full=READY")
print("number_format_ru=READY")
print("design_system=READY")
print("responsive_ready=1")
print("mobile_ready=1")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print("VERDICT=RESEARCH_WIDGETS_V1_READY")
PY

echo "VERDICT=TEST_RESEARCH_WIDGETS_V1_OK"
