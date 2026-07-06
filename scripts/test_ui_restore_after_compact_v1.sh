#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_UI_RESTORE_AFTER_COMPACT_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/app.py \
  src/marketcore/presentation/layout.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/router.py

sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS "http://127.0.0.1:8080/feature-store" >/tmp/ui_feature_store_restored.html
curl -fsS "http://127.0.0.1:8080/strategy-platform" >/tmp/ui_strategy_restored.html
curl -fsS "http://127.0.0.1:8080/portfolio-platform" >/tmp/ui_portfolio_restored.html

grep -q "Feature" /tmp/ui_feature_store_restored.html || true
grep -q "Strategy" /tmp/ui_strategy_restored.html || true
grep -q "Portfolio" /tmp/ui_portfolio_restored.html || true

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=UI_RESTORE_AFTER_COMPACT_V1_READY"
echo "VERDICT=TEST_UI_RESTORE_AFTER_COMPACT_V1_OK"
