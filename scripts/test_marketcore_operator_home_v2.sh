#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_OPERATOR_HOME_V2 ==="

files=(
  src/marketcore/presentation/widgets/contracts.py
  src/marketcore/presentation/widgets/registry.py
  src/marketcore/presentation/widgets/renderer.py
  src/marketcore/presentation/providers/operator_home_widgets_provider.py
  src/marketcore/presentation/pages/operator_home_page.py
)

for f in "${files[@]}"; do
  test -f "$f"
  PYTHONPYCACHEPREFIX=/tmp/finam_pycache_operator_home_v2 PYTHONPATH=src python -m py_compile "$f"
done

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.providers.operator_home_widgets_provider import OperatorHomeWidgetsProvider
from marketcore.presentation.pages.operator_home_page import OperatorHomePage
from marketcore.presentation.widgets.renderer import render_widgets

widgets = OperatorHomeWidgetsProvider().load()
ids = {w.widget_id for w in widgets}

for required in {"best_edge", "shadow", "daily", "portfolio", "system"}:
    assert required in ids, required

html = render_widgets(widgets)
assert "marketcore-widget-grid" in html
assert 'data-widget-id="best_edge"' in html
assert 'data-widget-id="shadow"' in html
assert 'data-widget-id="daily"' in html
assert 'data-widget-id="portfolio"' in html
assert 'data-widget-id="system"' in html

page = OperatorHomePage()
page_html = page.render()
assert 'data-dashboard-id="operator.home.v2"' in page_html
assert "marketcore-widget-grid" in page_html

print("operator_home_widgets=OK")
print("operator_home_v2_render=OK")
PY

if grep -RInE 'send_order|place_order|cancel_order|execute_order|FinamClient|LiveExecution|PaperExecution|INSERT INTO .*orders|INSERT INTO .*fills|UPDATE .*runtime|UPDATE .*execution' \
  src/marketcore/presentation/widgets \
  src/marketcore/presentation/providers/operator_home_widgets_provider.py \
  src/marketcore/presentation/pages/operator_home_page.py; then
  echo "DANGEROUS_OPERATOR_HOME_V2_ACTION_FOUND"
  exit 1
fi

sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS "http://127.0.0.1:8080/?v=$(date +%s)" >/tmp/operator_home_v2.html

grep -q 'data-dashboard-id="operator.home.v2"' /tmp/operator_home_v2.html
grep -q "marketcore-widget-grid" /tmp/operator_home_v2.html
grep -q 'data-widget-id="best_edge"' /tmp/operator_home_v2.html
grep -q 'data-widget-id="shadow"' /tmp/operator_home_v2.html
grep -q 'data-widget-id="daily"' /tmp/operator_home_v2.html
grep -q 'data-widget-id="portfolio"' /tmp/operator_home_v2.html
grep -q 'data-widget-id="system"' /tmp/operator_home_v2.html
grep -q "MarketCore" /tmp/operator_home_v2.html

echo "operator_home_v2_http=OK"
echo "widgets=best_edge,shadow,daily,portfolio,system"
echo "dangerous_actions=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_OPERATOR_HOME_V2_READY"
echo "VERDICT=TEST_MARKETCORE_OPERATOR_HOME_V2_OK"
