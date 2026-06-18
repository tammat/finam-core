#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST EQUITY WIRING BLOCK FINAL HEALTHCHECK V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/runtime/build_equity_wiring_block_final_healthcheck_v1.py

PYTHONPATH=src python3 src/scripts/runtime/build_equity_wiring_block_final_healthcheck_v1.py \
  | tee /tmp/equity_wiring_block_final_healthcheck_v1.log

grep -q "EQUITY_WIRING_BLOCK_FINAL_HEALTHCHECK_V1_OK" /tmp/equity_wiring_block_final_healthcheck_v1.log
grep -q "EQUITY_WIRING_FINAL_RUNTIME_ROW" /tmp/equity_wiring_block_final_healthcheck_v1.log
grep -q "EQUITY_WIRING_FINAL_GUARD_SUMMARY" /tmp/equity_wiring_block_final_healthcheck_v1.log
grep -q "EQUITY_WIRING_FINAL_TRADE_CONTEXT" /tmp/equity_wiring_block_final_healthcheck_v1.log
grep -q "EQUITY_WIRING_BLOCK_FINAL_HEALTHCHECK_SUMMARY" /tmp/equity_wiring_block_final_healthcheck_v1.log
grep -q "service_ts_ok=1" /tmp/equity_wiring_block_final_healthcheck_v1.log
grep -q "runtime_ok=1" /tmp/equity_wiring_block_final_healthcheck_v1.log
grep -q "guard_ok=1" /tmp/equity_wiring_block_final_healthcheck_v1.log
grep -q "trade_context_ok=1" /tmp/equity_wiring_block_final_healthcheck_v1.log
grep -q "discovery_ok=1" /tmp/equity_wiring_block_final_healthcheck_v1.log
grep -q "db_update=0" /tmp/equity_wiring_block_final_healthcheck_v1.log
grep -q "execution_changes_required=0" /tmp/equity_wiring_block_final_healthcheck_v1.log
grep -q "VERDICT=EQUITY_WIRING_BLOCK_FINAL_HEALTHCHECK_OK" /tmp/equity_wiring_block_final_healthcheck_v1.log

echo
echo "=== EQUITY WIRING BLOCK FINAL HEALTHCHECK SUMMARY ==="
grep -E "service_active_since_utc=|guard_rows_after_restart=|guard_expected_strategy_rows=|guard_other_strategy_rows=|trades_today=|strategy_missing_today=|timeframe_missing_today=|continuous_symbol_missing_today=|discovery_new=|service_ts_ok=|runtime_ok=|guard_ok=|trade_context_ok=|discovery_ok=|VERDICT=" \
  /tmp/equity_wiring_block_final_healthcheck_v1.log

echo TEST_EQUITY_WIRING_BLOCK_FINAL_HEALTHCHECK_V1_OK
