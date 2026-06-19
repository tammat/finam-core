#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST MULTI ASSET BREAKOUT DASHBOARD MSK TIME ALL PAGES V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/research/serve_multi_asset_breakout_dashboard_v1.py

PYTHONPATH=src MULTI_ASSET_DASHBOARD_PORT=18091 \
RUNTIME_ALLOW_TRADING=0 EXECUTION_ENABLED=0 REAL_TRADING_ENABLED=0 MULTI_ASSET_TELEGRAM_DRY_RUN=1 \
python3 src/scripts/research/serve_multi_asset_breakout_dashboard_v1.py >/tmp/multi_asset_dashboard_msk_time_all_pages_v1.log 2>&1 &
PID=$!

sleep 3

for url in summary history follow delivery; do
  curl --max-time 10 -fsS "http://127.0.0.1:18091/$url" >"/tmp/dashboard_msk_${url}.html"
done

kill "$PID"
wait "$PID" 2>/dev/null || true

grep -q "проверено МСК" /tmp/dashboard_msk_summary.html
grep -q "MSK" /tmp/dashboard_msk_summary.html
grep -q "MSK" /tmp/dashboard_msk_history.html
grep -q "MSK" /tmp/dashboard_msk_follow.html
grep -q "MSK" /tmp/dashboard_msk_delivery.html

if grep -E "2026-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]+)?\+00:00" \
  /tmp/dashboard_msk_history.html /tmp/dashboard_msk_follow.html /tmp/dashboard_msk_delivery.html; then
  echo "ERROR: UTC timestamp leaked into dashboard HTML"
  exit 1
fi

grep -q "Время сигнала, МСК" /tmp/dashboard_msk_delivery.html
grep -q "Время обработки, МСК" /tmp/dashboard_msk_delivery.html

echo "=== MSK TIME SAMPLE ==="
grep -E "проверено МСК|MSK|BRN6|BRQ6|GDU6" /tmp/dashboard_msk_delivery.html | head -30

echo "VERDICT=MULTI_ASSET_BREAKOUT_DASHBOARD_MSK_TIME_ALL_PAGES_READY"
echo TEST_MULTI_ASSET_BREAKOUT_DASHBOARD_MSK_TIME_ALL_PAGES_V1_OK
