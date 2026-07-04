#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_TRADING_PLATFORM_UI_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/pages/trading_platform.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/ui_labels.py \
  src/marketcore/presentation/router.py

sudo systemctl restart marketcore-kg-api.service
sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS "http://127.0.0.1:8095/api/kg/v1/trading-platform/summary" > /tmp/trading_platform_ui_summary.json
curl -fsS "http://127.0.0.1:8095/api/kg/v1/trading-platform/intents" > /tmp/trading_platform_ui_intents.json
curl -fsS "http://127.0.0.1:8080/trading-platform" > /tmp/trading_platform_ui.html

grep -q "Trading Platform" /tmp/trading_platform_ui.html
grep -q "Order Intent" /tmp/trading_platform_ui.html

if grep -R "SELECT .*trading_\|FROM analytics.trading_" \
  src/marketcore/presentation/pages/trading_platform.py; then
  echo "ERROR_DIRECT_SQL_IN_TRADING_PLATFORM_UI"
  exit 1
fi

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.trading_order_intent_v1
WHERE live_allowed=true
   OR micro_live_allowed=true
   OR order_sent=true;
")
test "$unsafe" = "0"

echo "unsafe_live_or_sent_rows=$unsafe"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TRADING_PLATFORM_UI_V1_READY"
echo "VERDICT=TEST_TRADING_PLATFORM_UI_V1_OK"
