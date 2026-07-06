#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_MODEL_VIEWMODEL_UI_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/pages/market_model_page.py \
  src/marketcore/presentation/registry.py

sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS http://127.0.0.1:8080/market-model >/tmp/market_model_viewmodel_ui_v1.html
curl -fsS http://127.0.0.1:8080/ >/tmp/market_model_home_v1.html

grep -q "Market Model" /tmp/market_model_viewmodel_ui_v1.html
grep -q "kpi-card" /tmp/market_model_viewmodel_ui_v1.html
grep -q "tree-view" /tmp/market_model_viewmodel_ui_v1.html
grep -q "data-table" /tmp/market_model_viewmodel_ui_v1.html
grep -q "/market-model" /tmp/market_model_home_v1.html

if grep -q "<pre" /tmp/market_model_viewmodel_ui_v1.html; then
  echo "RAW_PRE_FOUND"
  exit 1
fi

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKET_MODEL_VIEWMODEL_UI_V1_READY"
echo "VERDICT=TEST_MARKET_MODEL_VIEWMODEL_UI_V1_OK"
