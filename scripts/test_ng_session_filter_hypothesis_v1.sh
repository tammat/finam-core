#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST NG SESSION FILTER HYPOTHESIS V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/research/build_ng_session_filter_hypothesis_v1.py

PYTHONPATH=src python3 src/scripts/research/build_ng_session_filter_hypothesis_v1.py \
  | tee /tmp/ng_session_filter_hypothesis_v1.log

grep -q "NG_SESSION_FILTER_HYPOTHESIS_V1_OK" /tmp/ng_session_filter_hypothesis_v1.log
grep -q "NG_SESSION_FILTER_BY_SESSION" /tmp/ng_session_filter_hypothesis_v1.log
grep -q "NG_SESSION_FILTER_BY_SYMBOL_SESSION" /tmp/ng_session_filter_hypothesis_v1.log
grep -q "NG_SESSION_FILTER_HYPOTHESIS_SUMMARY" /tmp/ng_session_filter_hypothesis_v1.log
grep -q "db_update=0" /tmp/ng_session_filter_hypothesis_v1.log
grep -q "VERDICT=" /tmp/ng_session_filter_hypothesis_v1.log

echo
echo "=== NG SESSION FILTER SUMMARY ==="
grep -E "NG_SESSION_FILTER_SESSION_ROW|pairs_total=|symbols_count=|symbols=|positive_sessions=|confirmed_sessions=|total_net_pnl=|net_pnl_per_pair=|VERDICT=" \
  /tmp/ng_session_filter_hypothesis_v1.log

echo TEST_NG_SESSION_FILTER_HYPOTHESIS_V1_OK
