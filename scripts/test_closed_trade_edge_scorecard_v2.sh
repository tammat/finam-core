#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST CLOSED TRADE EDGE SCORECARD V2 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"

python3 -m py_compile \
  src/scripts/research/build_closed_trade_edge_scorecard_v2.py

PYTHONPATH=src python3 src/scripts/research/build_closed_trade_edge_scorecard_v2.py \
  | tee /tmp/closed_trade_edge_scorecard_v2.log

grep -q "CLOSED_TRADE_EDGE_SCORECARD_V2_OK" /tmp/closed_trade_edge_scorecard_v2.log
grep -q "VERDICT=CLOSED_TRADE_EDGE_SCORECARD_V2_READY" /tmp/closed_trade_edge_scorecard_v2.log
grep -q "CLOSED_TRADE_EDGE_V2_SUMMARY" /tmp/closed_trade_edge_scorecard_v2.log
grep -q "EDGE_V2_STRATEGY_ROW" /tmp/closed_trade_edge_scorecard_v2.log
grep -q "EDGE_V2_SYMBOL_ROW" /tmp/closed_trade_edge_scorecard_v2.log
grep -q "EDGE_KILLED_BY_COMMISSION" /tmp/closed_trade_edge_scorecard_v2.log
grep -q "EDGE_NEGATIVE_DAY" /tmp/closed_trade_edge_scorecard_v2.log
grep -q "OPEN_TAIL_REQUIRES_MTM" /tmp/closed_trade_edge_scorecard_v2.log

echo TEST_CLOSED_TRADE_EDGE_SCORECARD_V2_OK
