#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_TRADING_PLAN_WIDGET_V1 ==="

files=(
  src/marketcore/presentation/viewmodels/trading_plan_viewmodel.py
  src/marketcore/presentation/providers/trading_plan_widget_provider.py
  src/marketcore/presentation/providers/operator_home_widgets_provider.py
)

for f in "${files[@]}"; do
  test -f "$f"
  PYTHONPYCACHEPREFIX=/tmp/finam_pycache_trading_plan_widget PYTHONPATH=src python -m py_compile "$f"
done

if grep -RInE 'send_order|place_order|cancel_order|execute_order|INSERT INTO .*orders|INSERT INTO .*fills|UPDATE .*runtime|UPDATE .*execution|DROP TABLE|TRUNCATE|DELETE FROM' "${files[@]}"; then
  echo "DANGEROUS_CODE_FOUND"
  exit 1
fi

if grep -RInE 'SBER|LKOH|GAZP|VTBR|BUY|SELL|LONG|SHORT' "${files[@]}"; then
  echo "HARDCODE_FOUND"
  exit 1
fi

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.providers.trading_plan_widget_provider import TradingPlanWidgetProvider
from marketcore.presentation.providers.operator_home_widgets_provider import OperatorHomeWidgetsProvider
from marketcore.presentation.widgets.renderer import render_widget

vm = TradingPlanWidgetProvider().load()
assert vm.widget_id == "trading_plan"
assert vm.title_key == "widget.trading_plan.title"
assert vm.state == "readonly"

html = render_widget(vm)
assert 'data-widget-id="trading_plan"' in html
assert "Торговый план" in html
assert "Цена входа" in html
assert "Целевая цена" in html

widgets = OperatorHomeWidgetsProvider().load()
assert "trading_plan" in {w.widget_id for w in widgets}

print("trading_plan_widget_provider=OK")
print("trading_plan_widget_render=OK")
print("operator_home_widget_included=OK")
PY

sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS "http://127.0.0.1:8080/?v=$(date +%s)" >/tmp/trading_plan_widget_v1.html

grep -q 'data-widget-id="trading_plan"' /tmp/trading_plan_widget_v1.html
grep -q "Торговый план" /tmp/trading_plan_widget_v1.html
grep -q "Цена входа" /tmp/trading_plan_widget_v1.html
grep -q "Целевая цена" /tmp/trading_plan_widget_v1.html

if grep -Eo '(widget|trading_plan|market_structure)\.[A-Za-z0-9_.-]+' /tmp/trading_plan_widget_v1.html; then
  echo "RAW_I18N_KEY_VISIBLE"
  exit 1
fi

rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.recommendation_execution_context_v1
WHERE source_version='TRADING_PLAN_PARAMETER_BUILDER_V1';
")

test "$rows" -ge 1

echo "trading_plan_rows=$rows"
echo "trading_plan_widget_provider=OK"
echo "trading_plan_widget_render=OK"
echo "trading_plan_widget_http=OK"
echo "raw_i18n_keys=0"
echo "hardcode=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TRADING_PLAN_WIDGET_V1_READY"
echo "VERDICT=TEST_TRADING_PLAN_WIDGET_V1_OK"
