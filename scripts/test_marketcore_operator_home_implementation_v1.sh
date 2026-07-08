#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_OPERATOR_HOME_IMPLEMENTATION_V1 ==="

files=(
  src/marketcore/presentation/providers/operator_home_provider.py
  src/marketcore/presentation/pages/operator_home_page.py
  src/marketcore/presentation/components/layout/status_bar.py
  src/marketcore/presentation/dashboard/viewmodel.py
  src/marketcore/presentation/dashboard/renderer.py
)

for f in "${files[@]}"; do
  test -f "$f"
  PYTHONPYCACHEPREFIX=/tmp/finam_pycache_operator_home PYTHONPATH=src python -m py_compile "$f"
done

PYTHONPYCACHEPREFIX=/tmp/finam_pycache_operator_home PYTHONPATH=src python - <<'PY'
from marketcore.presentation.providers.operator_home_provider import OperatorHomeProvider
from marketcore.presentation.pages.operator_home_page import OperatorHomePage
from marketcore.presentation.dashboard.renderer import render_dashboard
from marketcore.presentation.components.layout.status_bar import render_status_bar

vm = OperatorHomeProvider().load()
assert vm.dashboard_id == "operator.home"
assert vm.safety.runtime_allowed == 0
assert vm.safety.execution_allowed == 0
assert vm.safety.micro_live_allowed == 0
assert vm.safety.orders_changed == 0
assert vm.safety.fills_changed == 0
assert len(vm.kpis) >= 4
assert vm.table.rows_count >= 1

html = render_dashboard(vm)
assert 'data-dashboard-id="operator.home"' in html
assert "page.operator_home.title" in html
assert "Best Edge" in html
assert "Shadow" in html
assert "Daily Analytics" in html

page = OperatorHomePage()
assert page.route == "/"
assert "operator.home" in page.render()

status = render_status_bar()
assert "marketcore-status-bar" in status

import re
assert re.search(r"\d{2}\.\d{2}\.\d{2} \d{2}:\d{2}", status), status

print("operator_home_provider=OK")
print("operator_home_render=OK")
print("status_bar_datetime_format=DD.MM.YY HH:MM")
PY

if grep -RInE 'send_order|place_order|cancel_order|execute_order|FinamClient|LiveExecution|PaperExecution|INSERT INTO .*orders|INSERT INTO .*fills|UPDATE .*runtime|UPDATE .*execution' \
  src/marketcore/presentation/providers/operator_home_provider.py \
  src/marketcore/presentation/pages/operator_home_page.py; then
  echo "DANGEROUS_OPERATOR_HOME_ACTION_FOUND"
  exit 1
fi

sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS "http://127.0.0.1:8080/?v=$(date +%s)" >/tmp/operator_home_v1.html

grep -q 'data-dashboard-id="operator.home"' /tmp/operator_home_v1.html
grep -q "page.operator_home.title" /tmp/operator_home_v1.html
grep -q "Best Edge" /tmp/operator_home_v1.html
grep -q "Shadow" /tmp/operator_home_v1.html
grep -q "Daily Analytics" /tmp/operator_home_v1.html
grep -q "marketcore-status-bar" /tmp/operator_home_v1.html
grep -Eq '[0-9]{2}\.[0-9]{2}\.[0-9]{2} [0-9]{2}:[0-9]{2}' /tmp/operator_home_v1.html

echo "operator_home_http=OK"
echo "datetime_format=DD.MM.YY HH:MM"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_OPERATOR_HOME_IMPLEMENTATION_V1_READY"
echo "VERDICT=TEST_MARKETCORE_OPERATOR_HOME_IMPLEMENTATION_V1_OK"
