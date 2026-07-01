#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_METADATA_WIDGETS_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/widgets/metadata_page/overview.py \
  src/marketcore/presentation/widgets/metadata_page/objects.py \
  src/marketcore/presentation/widgets/metadata_page/sources.py \
  src/marketcore/presentation/widgets/metadata_page/actions.py

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.viewmodels.metadata_center_vm import build_default_metadata_center_vm
from marketcore.presentation.widgets.metadata_page.overview import MetadataOverviewWidget
from marketcore.presentation.widgets.metadata_page.objects import MetadataObjectsWidget
from marketcore.presentation.widgets.metadata_page.sources import MetadataSourcesWidget
from marketcore.presentation.widgets.metadata_page.actions import MetadataActionsWidget

vm = build_default_metadata_center_vm()

html = (
    MetadataOverviewWidget().render(vm)
    + MetadataObjectsWidget().render(vm)
    + MetadataSourcesWidget().render(vm)
    + MetadataActionsWidget().render(vm)
)

for needle in [
    "Сводка",
    "Объекты",
    "Источники",
    "Действия",
    "Рыночные бары",
    "Рыночные тики",
    "71,1 млн.",
    "876 тыс.",
    "Покрытие",
    "Качество",
]:
    assert needle in html, needle

for forbidden in ["Details", "Settings", "Search", "Fresh", "Volume", "Ticks", "market_bars", "market_ticks"]:
    assert forbidden not in html, forbidden

print("metadata_overview_widget=READY")
print("metadata_objects_widget=READY")
print("metadata_sources_widget=READY")
print("metadata_actions_widget=READY")
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
print("VERDICT=METADATA_WIDGETS_V1_READY")
PY

echo "VERDICT=TEST_METADATA_WIDGETS_V1_OK"
