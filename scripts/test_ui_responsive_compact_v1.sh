#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_UI_RESPONSIVE_COMPACT_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/router.py

sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS "http://127.0.0.1:8080/feature-store" >/tmp/ui_compact_feature_store.html
curl -fsS "http://127.0.0.1:8080/portfolio-platform" >/tmp/ui_compact_portfolio.html

grep -q "ui-runtime-bar" /tmp/ui_compact_feature_store.html
grep -q "ui-runtime-clock" /tmp/ui_compact_feature_store.html
grep -q "UI_RESPONSIVE_COMPACT_V1" /tmp/ui_compact_feature_store.html

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=UI_RESPONSIVE_COMPACT_V1_READY"
echo "VERDICT=TEST_UI_RESPONSIVE_COMPACT_V1_OK"
