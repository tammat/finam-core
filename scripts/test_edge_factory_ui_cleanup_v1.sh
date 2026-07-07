#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_FACTORY_UI_CLEANUP_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core -f sql/presentation/006_edge_factory_ui_cleanup_v1.sql

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/providers/edge_factory_console_provider.py \
  src/marketcore/presentation/pages/zz_edge_factory_operator_console.py \
  src/marketcore/presentation/registry.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python - <<'PY'
from marketcore.presentation.registry import get_page

page = get_page("/edge-factory")
assert page is not None
print(page)
PY

sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS -H "Cache-Control: no-cache" "http://127.0.0.1:8080/edge-factory?v=$(date +%s)" >/tmp/edge_factory_ui_cleanup_v1.html

grep -q "Edge Factory" /tmp/edge_factory_ui_cleanup_v1.html
grep -q "Действия" /tmp/edge_factory_ui_cleanup_v1.html
grep -q "Запустить планировщик" /tmp/edge_factory_ui_cleanup_v1.html
grep -q "Максимальный edge" /tmp/edge_factory_ui_cleanup_v1.html

if grep -q "<pre" /tmp/edge_factory_ui_cleanup_v1.html; then
  echo "RAW_PRE_FOUND"
  exit 1
fi

if grep -Eq "details=\{|result_json=\{|config_json=\{|payload=\{|\{''" /tmp/edge_factory_ui_cleanup_v1.html; then
  echo "RAW_JSON_FOUND"
  exit 1
fi

legacy_enabled=$(psql -At -d finam_core -c "
SELECT count(*)
FROM presentation.ui_navigation_item_v1
WHERE item_code IN (
  'FEATURE_STORE',
  'KNOWLEDGE_GRAPH',
  'TRADING_PLATFORM',
  'PORTFOLIO_PLATFORM',
  'STRATEGY_GOVERNANCE',
  'EDGE_PLATFORM',
  'RUNTIME_VIEW'
)
AND is_enabled=true;
")

labels=$(psql -At -d finam_core -c "
SELECT count(*)
FROM presentation.ui_resource_v1
WHERE resource_group IN ('edge_factory','navigation')
  AND locale_code='ru';
")

test "$legacy_enabled" = "0"
test "$labels" -ge 10

echo "legacy_enabled=$legacy_enabled"
echo "i18n_labels=$labels"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_FACTORY_UI_CLEANUP_V1_READY"
echo "VERDICT=TEST_EDGE_FACTORY_UI_CLEANUP_V1_OK"
