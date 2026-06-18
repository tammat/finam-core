#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST RUNTIME ACCUMULATION HEALTHCHECK V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/runtime/build_runtime_accumulation_healthcheck_v1.py

PYTHONPATH=src python3 src/scripts/runtime/build_runtime_accumulation_healthcheck_v1.py \
  | tee /tmp/runtime_accumulation_healthcheck_v1.log

grep -q "RUNTIME_ACCUMULATION_HEALTHCHECK_V1_OK" /tmp/runtime_accumulation_healthcheck_v1.log
grep -q "RUNTIME_ACTIVE_UNIVERSE_ROWS" /tmp/runtime_accumulation_healthcheck_v1.log
grep -q "TRADE_ACCUMULATION_TODAY" /tmp/runtime_accumulation_healthcheck_v1.log
grep -q "TRADE_ACCUMULATION_BY_SYMBOL" /tmp/runtime_accumulation_healthcheck_v1.log
grep -q "SIGNAL_DISCOVERY_HEALTH" /tmp/runtime_accumulation_healthcheck_v1.log
grep -q "RUNTIME_ACCUMULATION_HEALTHCHECK_SUMMARY" /tmp/runtime_accumulation_healthcheck_v1.log
grep -q "db_update=0" /tmp/runtime_accumulation_healthcheck_v1.log
grep -q "VERDICT=" /tmp/runtime_accumulation_healthcheck_v1.log

echo
echo "=== RUNTIME ACCUMULATION HEALTHCHECK SUMMARY ==="
grep -E "RUNTIME_ACTIVE_UNIVERSE_ROW|TRADE_ACCUMULATION_SYMBOL_ROW|MARKET_BARS_FRESHNESS_ROW|runtime_rows=|runtime_equities=|runtime_equities_enabled=|equity_trade_rows=|market_bar_equity_rows=|trades_today=|discovery_new=|equity_accumulation_reason=|failures=|VERDICT=" \
  /tmp/runtime_accumulation_healthcheck_v1.log

echo TEST_RUNTIME_ACCUMULATION_HEALTHCHECK_V1_OK
