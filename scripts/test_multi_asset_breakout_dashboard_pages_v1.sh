#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST MULTI ASSET BREAKOUT DASHBOARD PAGES V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/research/serve_multi_asset_breakout_dashboard_v1.py

PYTHONPATH=src MULTI_ASSET_DASHBOARD_PORT=18089 \
RUNTIME_ALLOW_TRADING=0 EXECUTION_ENABLED=0 REAL_TRADING_ENABLED=0 MULTI_ASSET_TELEGRAM_DRY_RUN=1 \
python3 src/scripts/research/serve_multi_asset_breakout_dashboard_v1.py >/tmp/multi_asset_dashboard_pages_v1.log 2>&1 &
PID=$!

sleep 3

for url in summary history blockers ready rows follow journal api/current; do
  curl --max-time 10 -fsS "http://127.0.0.1:18089/$url" >/tmp/dashboard_page_${url//\//_}.out
done

grep -q "Сводка" /tmp/dashboard_page_summary.out
grep -q "История за день" /tmp/dashboard_page_history.out
grep -q "Причины блокировки" /tmp/dashboard_page_blockers.out
grep -q "Готовые сигналы" /tmp/dashboard_page_ready.out
grep -q "Текущая таблица наблюдения" /tmp/dashboard_page_rows.out
grep -q "Follow-through scorecard" /tmp/dashboard_page_follow.out
grep -q "Журнал Telegram sender" /tmp/dashboard_page_journal.out
grep -q '"dashboard": "MULTI_ASSET_BREAKOUT_SIGNAL_QUALITY_OBSERVATION_V1"' /tmp/dashboard_page_api_current.out
grep -q '"execution_enabled": "0"' /tmp/dashboard_page_api_current.out
grep -q '"real_trading_enabled": "0"' /tmp/dashboard_page_api_current.out

kill "$PID"
wait "$PID" 2>/dev/null || true

echo "=== DASHBOARD PAGES LOG ==="
cat /tmp/multi_asset_dashboard_pages_v1.log

echo "VERDICT=MULTI_ASSET_BREAKOUT_DASHBOARD_PAGES_READY"
echo TEST_MULTI_ASSET_BREAKOUT_DASHBOARD_PAGES_V1_OK
