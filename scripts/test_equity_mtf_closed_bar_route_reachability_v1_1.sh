#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST EQUITY MTF CLOSED BAR ROUTE REACHABILITY V1.1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/research/build_equity_mtf_closed_bar_route_reachability_v1_1.py

PYTHONPATH=src ACTIVE_SINCE_UTC="${ACTIVE_SINCE_UTC:-2026-06-19 05:55:21+00}" \
python3 src/scripts/research/build_equity_mtf_closed_bar_route_reachability_v1_1.py \
  | tee /tmp/equity_mtf_closed_bar_route_reachability_v1_1.log

grep -q "EQUITY_MTF_CLOSED_BAR_ROUTE_REACHABILITY_V1_1_OK" /tmp/equity_mtf_closed_bar_route_reachability_v1_1.log
grep -q "EQUITY_MTF_CLOSED_BAR_ROUTE_REACHABILITY_V1_1_SUMMARY" /tmp/equity_mtf_closed_bar_route_reachability_v1_1.log
grep -q "bars_after_restart=" /tmp/equity_mtf_closed_bar_route_reachability_v1_1.log
grep -q "guard_after_restart=" /tmp/equity_mtf_closed_bar_route_reachability_v1_1.log
grep -q "signals_after_restart=" /tmp/equity_mtf_closed_bar_route_reachability_v1_1.log
grep -q "VERDICT=" /tmp/equity_mtf_closed_bar_route_reachability_v1_1.log
grep -q "db_update=0" /tmp/equity_mtf_closed_bar_route_reachability_v1_1.log

echo
echo "=== EQUITY MTF CLOSED BAR ROUTE REACHABILITY V1.1 SUMMARY ==="
grep -E "EQUITY_MTF_RESTART_AWARE_RUNTIME_ROW|EQUITY_MTF_RESTART_AWARE_BAR_ROW|EQUITY_MTF_RESTART_AWARE_GUARD_ROW|EQUITY_MTF_RESTART_AWARE_SIGNAL_ROW|bars_after_restart=|guard_after_restart=|signals_after_restart=|VERDICT=" \
  /tmp/equity_mtf_closed_bar_route_reachability_v1_1.log

echo TEST_EQUITY_MTF_CLOSED_BAR_ROUTE_REACHABILITY_V1_1_OK
