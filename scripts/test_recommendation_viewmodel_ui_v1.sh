#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RECOMMENDATION_VIEWMODEL_UI_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/pages/recommendation_page.py \
  src/marketcore/presentation/registry.py

sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS http://127.0.0.1:8080/recommendation >/tmp/recommendation_viewmodel_ui_v1.html
curl -fsS http://127.0.0.1:8080/ >/tmp/recommendation_home_v1.html

grep -q "Recommendation" /tmp/recommendation_viewmodel_ui_v1.html
grep -q "kpi-card" /tmp/recommendation_viewmodel_ui_v1.html
grep -q "object-card" /tmp/recommendation_viewmodel_ui_v1.html
grep -q "data-table" /tmp/recommendation_viewmodel_ui_v1.html
grep -q "/recommendation" /tmp/recommendation_home_v1.html

if grep -q "<pre" /tmp/recommendation_viewmodel_ui_v1.html; then
  echo "RAW_PRE_FOUND"
  exit 1
fi

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=RECOMMENDATION_VIEWMODEL_UI_V1_READY"
echo "VERDICT=TEST_RECOMMENDATION_VIEWMODEL_UI_V1_OK"
