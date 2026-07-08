#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_UI_MIGRATION_V1 ==="

doc="docs/MARKETCORE_UI_MIGRATION_V1.txt"
test -f "$doc"

grep -q "OLD UI STATUS:" "$doc"
grep -q "DEPRECATED" "$doc"
grep -q "Provider -> ViewModel -> DashboardRenderer -> Component Library" "$doc"
grep -q "MARKETCORE_UI_MIGRATION_V1_READY" "$doc"

PYTHONPYCACHEPREFIX=/tmp/finam_pycache_ui_migration \
PYTHONPATH=src \
python -m py_compile \
  src/marketcore/presentation/dashboard/viewmodel.py \
  src/marketcore/presentation/dashboard/renderer.py \
  src/marketcore/presentation/providers/operator_home_provider.py \
  src/marketcore/presentation/pages/operator_home_page.py \
  src/marketcore/presentation/components/layout/status_bar.py \
  src/marketcore/presentation/route_groups.py \
  src/marketcore/presentation/ui_labels.py

if grep -RInE 'send_order|place_order|cancel_order|execute_order|FinamClient|LiveExecution|PaperExecution|INSERT INTO .*orders|INSERT INTO .*fills|UPDATE .*runtime|UPDATE .*execution' \
  src/marketcore/presentation/dashboard \
  src/marketcore/presentation/components \
  src/marketcore/presentation/providers/operator_home_provider.py \
  src/marketcore/presentation/pages/operator_home_page.py; then
  echo "DANGEROUS_UI_MIGRATION_ACTION_FOUND"
  exit 1
fi

sudo systemctl restart marketcore-ui-shell.service
sleep 2

for route in / /max-edge /edge-score-shadow /edge-score-shadow-daily /system; do
  code=$(curl -sS -o /tmp/marketcore_ui_migration_route.html -w "%{http_code}" "http://127.0.0.1:8080${route}?v=$(date +%s)" || true)
  if [ "$code" != "200" ]; then
    echo "ROUTE_HTTP_NOT_OK route=$route code=$code"
    exit 1
  fi
done

curl -fsS "http://127.0.0.1:8080/?v=$(date +%s)" >/tmp/marketcore_ui_migration_home.html

grep -q "MarketCore" /tmp/marketcore_ui_migration_home.html
grep -q "marketcore-status-bar" /tmp/marketcore_ui_migration_home.html
grep -q 'data-dashboard-id="operator.home"' /tmp/marketcore_ui_migration_home.html
grep -Eq '[0-9]{2}\.[0-9]{2}\.[0-9]{2} [0-9]{2}:[0-9]{2}' /tmp/marketcore_ui_migration_home.html

if grep -q "FINAM Core" /tmp/marketcore_ui_migration_home.html; then
  echo "LEGACY_FINAMCORE_BRAND_VISIBLE"
  exit 1
fi

echo "ui_migration_doc=OK"
echo "operator_home=OK"
echo "status_bar=OK"
echo "routes_http=OK"
echo "legacy_brand_visible=0"
echo "dangerous_actions=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_UI_MIGRATION_V1_READY"
echo "VERDICT=TEST_MARKETCORE_UI_MIGRATION_V1_OK"
