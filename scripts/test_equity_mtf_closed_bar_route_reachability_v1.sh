#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST EQUITY MTF CLOSED BAR ROUTE REACHABILITY V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/research/build_equity_mtf_closed_bar_route_reachability_v1.py

PYTHONPATH=src LOOKBACK_MINUTES="${LOOKBACK_MINUTES:-240}" \
python3 src/scripts/research/build_equity_mtf_closed_bar_route_reachability_v1.py \
  | tee /tmp/equity_mtf_closed_bar_route_reachability_v1.log

grep -q "EQUITY_MTF_CLOSED_BAR_ROUTE_REACHABILITY_V1_OK" /tmp/equity_mtf_closed_bar_route_reachability_v1.log
grep -q "EQUITY_MTF_CLOSED_BAR_ROUTE_REACHABILITY_SUMMARY" /tmp/equity_mtf_closed_bar_route_reachability_v1.log
grep -q "runtime_ok=" /tmp/equity_mtf_closed_bar_route_reachability_v1.log
grep -q "fresh_bars_ok=" /tmp/equity_mtf_closed_bar_route_reachability_v1.log
grep -q "VERDICT=" /tmp/equity_mtf_closed_bar_route_reachability_v1.log
grep -q "db_update=0" /tmp/equity_mtf_closed_bar_route_reachability_v1.log

echo
echo "=== EQUITY MTF CLOSED BAR ROUTE REACHABILITY SUMMARY ==="
grep -E "EQUITY_MTF_RUNTIME_ROW|EQUITY_MTF_BAR_SUMMARY_ROW|EQUITY_MTF_GUARD_REACHABILITY_ROW|EQUITY_MTF_SIGNAL_REACHABILITY_ROW|runtime_ok=|fresh_bars_ok=|fresh_guard_or_signal_rows=|VERDICT=" \
  /tmp/equity_mtf_closed_bar_route_reachability_v1.log

echo TEST_EQUITY_MTF_CLOSED_BAR_ROUTE_REACHABILITY_V1_OK
