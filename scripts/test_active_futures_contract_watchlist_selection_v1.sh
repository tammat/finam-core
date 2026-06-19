#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST ACTIVE FUTURES CONTRACT WATCHLIST SELECTION V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/research/build_active_futures_contract_watchlist_selection_v1.py

PYTHONPATH=src FUTURES_PREFIXES="${FUTURES_PREFIXES:-BR,NG,GD}" \
python3 src/scripts/research/build_active_futures_contract_watchlist_selection_v1.py \
  | tee /tmp/active_futures_contract_watchlist_selection_v1.log

grep -q "ACTIVE_FUTURES_CONTRACT_WATCHLIST_SELECTION_V1_OK" /tmp/active_futures_contract_watchlist_selection_v1.log
grep -q "ACTIVE_FUTURES_CONTRACT_WATCHLIST_SELECTION_SUMMARY" /tmp/active_futures_contract_watchlist_selection_v1.log
grep -q "ACTIVE_FUTURES_CONTRACT_SELECTION_ROW" /tmp/active_futures_contract_watchlist_selection_v1.log
grep -q "PRIMARY_WATCH" /tmp/active_futures_contract_watchlist_selection_v1.log
grep -q "VERDICT=" /tmp/active_futures_contract_watchlist_selection_v1.log
grep -q "db_update=0" /tmp/active_futures_contract_watchlist_selection_v1.log

echo
echo "=== ACTIVE FUTURES CONTRACT WATCHLIST SELECTION SUMMARY ==="
grep -E "ACTIVE_FUTURES_CONTRACT_SELECTION_ROW|families_total=|candidate_rows_total=|selected_total=|primary_total=|secondary_total=|research_total=|VERDICT=" \
  /tmp/active_futures_contract_watchlist_selection_v1.log

echo TEST_ACTIVE_FUTURES_CONTRACT_WATCHLIST_SELECTION_V1_OK
