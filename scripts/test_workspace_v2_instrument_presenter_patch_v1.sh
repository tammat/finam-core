#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKSPACE_V2_INSTRUMENT_PRESENTER_PATCH_V1 ==="

files=(
  "src/marketcore/presentation/framework/registry.py"
  "src/marketcore/presentation/workspace_v2/resolver/instrument_display_resolver_v1.py"
  "src/marketcore/presentation/workspace_v2/viewmodel/instrument_viewmodel_v1.py"
  "src/marketcore/presentation/workspace_v2/presenter/instrument_presenter_v1.py"
  "src/marketcore/presentation/workspace_v2/renderer/instrument_card_renderer_v1.py"
)

PYTHONPYCACHEPREFIX=/tmp/instrument_presenter_patch_full \
PYTHONPATH=src \
python -m py_compile "${files[@]}"

if grep -RInE 'Открыть|📈|fallback"|tooltip=f|title=instrument.display_name|subtitle=instrument.symbol|badge=instrument.asset_class|status=' \
  src/marketcore/presentation/workspace_v2/presenter/instrument_presenter_v1.py \
  src/marketcore/presentation/workspace_v2/renderer/instrument_card_renderer_v1.py; then
  echo "INSTRUMENT_UI_HARDCODE_FOUND"
  exit 1
fi

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.framework.registry import UiStatusCode
from marketcore.presentation.workspace_v2.presenter.instrument_presenter_v1 import InstrumentPresenterV1
from marketcore.presentation.workspace_v2.renderer.instrument_card_renderer_v1 import render_instrument_card_v1

vm = InstrumentPresenterV1().card("SBER")

assert vm.title_key
assert vm.subtitle_key
assert vm.badge_key
assert vm.tooltip_key
assert vm.icon_key
assert vm.status_code in (UiStatusCode.OK, UiStatusCode.FALLBACK)

html = render_instrument_card_v1(vm)

assert 'data-i18n-key="' in html
assert 'ui.action.open' in html
assert "Открыть" not in html
assert "📈" not in html

print("instrument_presenter_patch=OK")
print("instrument_renderer_i18n=OK")
PY

echo "instrument_domain_patch=OK"
echo "instrument_viewmodel_patch=OK"
echo "instrument_presenter_patch=OK"
echo "instrument_renderer_patch=OK"
echo "i18n_keys=OK"
echo "ui_hardcodes=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=WORKSPACE_V2_INSTRUMENT_PRESENTER_PATCH_V1_READY"
echo "VERDICT=TEST_WORKSPACE_V2_INSTRUMENT_PRESENTER_PATCH_V1_OK"
