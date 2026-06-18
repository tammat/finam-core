#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST CLOSED TRADE EDGE SCORECARD V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"

python3 -m py_compile \
  src/scripts/research/build_closed_trade_edge_scorecard_v1.py

PYTHONPATH=src python3 src/scripts/research/build_closed_trade_edge_scorecard_v1.py \
  | tee /tmp/closed_trade_edge_scorecard_v1.log

grep -q "CLOSED_TRADE_EDGE_SCORECARD_V1_OK" /tmp/closed_trade_edge_scorecard_v1.log
grep -q "VERDICT=CLOSED_TRADE_EDGE_SCORECARD_READY" /tmp/closed_trade_edge_scorecard_v1.log
grep -q "CLOSED_TRADE_EDGE_SUMMARY" /tmp/closed_trade_edge_scorecard_v1.log
grep -q "EDGE_ROW" /tmp/closed_trade_edge_scorecard_v1.log

echo TEST_CLOSED_TRADE_EDGE_SCORECARD_V1_OK
