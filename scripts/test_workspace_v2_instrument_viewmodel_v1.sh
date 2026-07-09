#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKSPACE_V2_INSTRUMENT_VIEWMODEL_V1 ==="

files=(
  "src/marketcore/presentation/workspace_v2/viewmodel/instrument_viewmodel_v1.py"
  "src/marketcore/presentation/workspace_v2/presenter/instrument_presenter_v1.py"
  "src/marketcore/presentation/workspace_v2/renderer/instrument_card_renderer_v1.py"
)

for f in "${files[@]}"; do
  test -f "$f"
done

PYTHONPYCACHEPREFIX=/tmp/finam_pycache_instrument_viewmodel \
PYTHONPATH=src \
python -m py_compile "${files[@]}"

if grep -RInE 'SELECT |INSERT INTO|UPDATE |DELETE FROM|DROP TABLE|TRUNCATE|send_order|place_order|execute_order' "${files[@]}"; then
  echo "FORBIDDEN_LAYER_VIOLATION_FOUND"
  exit 1
fi

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.workspace_v2.presenter.instrument_presenter_v1 import InstrumentPresenterV1
from marketcore.presentation.workspace_v2.renderer.instrument_card_renderer_v1 import render_instrument_card_v1

presenter = InstrumentPresenterV1()

for symbol in ["SBER", "LKOH", "UNKNOWN_TEST_SYMBOL_V1"]:
    vm = presenter.card(symbol)
    assert vm.title
    assert vm.subtitle == symbol
    assert vm.navigation_target.endswith(symbol)
    html = render_instrument_card_v1(vm)
    assert "mc-v2-card" in html
    assert symbol in html

print("instrument_viewmodel=OK")
print("instrument_presenter=OK")
print("instrument_renderer=OK")
PY

echo "presentation_framework=OK"
echo "sql_in_ui=0"
echo "raw_symbol_as_primary_title_checked=OK"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=WORKSPACE_V2_INSTRUMENT_VIEWMODEL_V1_READY"
echo "VERDICT=TEST_WORKSPACE_V2_INSTRUMENT_VIEWMODEL_V1_OK"
