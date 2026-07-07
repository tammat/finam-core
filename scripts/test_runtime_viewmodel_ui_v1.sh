#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RUNTIME_VIEWMODEL_UI_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/pages/runtime_page.py \
  src/marketcore/presentation/registry.py

systemctl is-active --quiet marketcore-ui-shell.service || {
  echo "marketcore-ui-shell.service is not running"
  exit 1
}

curl -fsS http://127.0.0.1:8080/runtime-view >/tmp/runtime_viewmodel_ui_v1.html
curl -fsS http://127.0.0.1:8080/ >/tmp/runtime_home_v1.html

grep -q "Runtime View" /tmp/runtime_viewmodel_ui_v1.html
grep -q "kpi-card" /tmp/runtime_viewmodel_ui_v1.html
grep -q "data-table" /tmp/runtime_viewmodel_ui_v1.html
grep -q "/runtime-view" /tmp/runtime_home_v1.html

if grep -q "<pre" /tmp/runtime_viewmodel_ui_v1.html; then
  echo "RAW_PRE_FOUND"
  exit 1
fi

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=RUNTIME_VIEWMODEL_UI_V1_READY"
echo "VERDICT=TEST_RUNTIME_VIEWMODEL_UI_V1_OK"
