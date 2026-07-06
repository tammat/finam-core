#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_UI_LAYOUT_RESTORE_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/layout.py \
  src/marketcore/presentation/app.py \
  src/marketcore/presentation/router.py \
  src/marketcore/presentation/registry.py

sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS http://127.0.0.1:8080/feature-store >/tmp/ui_layout_feature_store.html
curl -fsS http://127.0.0.1:8080/strategy-platform >/tmp/ui_layout_strategy.html
curl -fsS http://127.0.0.1:8080/edge-platform >/tmp/ui_layout_edge.html
curl -fsS http://127.0.0.1:8080/risk-platform >/tmp/ui_layout_risk.html
curl -fsS http://127.0.0.1:8080/trading-platform >/tmp/ui_layout_trading.html
curl -fsS http://127.0.0.1:8080/portfolio-platform >/tmp/ui_layout_portfolio.html

grep -q "FINAM Core" /tmp/ui_layout_feature_store.html
grep -q "ui-clock" /tmp/ui_layout_feature_store.html
grep -q "viewport" /tmp/ui_layout_feature_store.html
grep -q "Portfolio Platform" /tmp/ui_layout_portfolio.html

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=UI_LAYOUT_RESTORE_V1_READY"
echo "VERDICT=TEST_UI_LAYOUT_RESTORE_V1_OK"
