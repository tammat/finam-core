#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST ACTIVE FUTURES CONTRACT WATCHLIST EXPIRY PLAN V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/research/build_active_futures_contract_watchlist_expiry_plan_v1.py

PYTHONPATH=src FUTURES_PREFIXES="${FUTURES_PREFIXES:-BR,NG,GD}" \
python3 src/scripts/research/build_active_futures_contract_watchlist_expiry_plan_v1.py \
  | tee /tmp/active_futures_contract_watchlist_expiry_plan_v1.log

grep -q "ACTIVE_FUTURES_CONTRACT_WATCHLIST_EXPIRY_PLAN_V1_OK" /tmp/active_futures_contract_watchlist_expiry_plan_v1.log
grep -q "ACTIVE_FUTURES_CONTRACT_WATCHLIST_EXPIRY_PLAN_SUMMARY" /tmp/active_futures_contract_watchlist_expiry_plan_v1.log
grep -q "ACTIVE_FUTURES_CONTRACT_ROW" /tmp/active_futures_contract_watchlist_expiry_plan_v1.log
grep -q "freshness=" /tmp/active_futures_contract_watchlist_expiry_plan_v1.log
grep -q "expiry_bucket=" /tmp/active_futures_contract_watchlist_expiry_plan_v1.log
grep -q "watch_candidate=" /tmp/active_futures_contract_watchlist_expiry_plan_v1.log
grep -q "VERDICT=" /tmp/active_futures_contract_watchlist_expiry_plan_v1.log
grep -q "db_update=0" /tmp/active_futures_contract_watchlist_expiry_plan_v1.log
grep -q "futures_prefixes=BR,NG,GD" /tmp/active_futures_contract_watchlist_expiry_plan_v1.log

echo
echo "=== ACTIVE FUTURES CONTRACT WATCHLIST EXPIRY SUMMARY ==="
grep -E "ACTIVE_FUTURES_CONTRACT_ROW|rows_total=|fresh_rows=|expired_rows=|stale_or_dead_rows=|watch_candidates=|VERDICT=" \
  /tmp/active_futures_contract_watchlist_expiry_plan_v1.log | head -260

echo TEST_ACTIVE_FUTURES_CONTRACT_WATCHLIST_EXPIRY_PLAN_V1_OK
