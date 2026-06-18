#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST SIGNAL CLASS EDGE SCORECARD V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile \
  src/scripts/research/build_signal_class_edge_scorecard_v1.py

SIGNAL_CLASS_EDGE_LOOKBACK="${SIGNAL_CLASS_EDGE_LOOKBACK:-30 days}" \
SIGNAL_CLASS_EDGE_LIMIT="${SIGNAL_CLASS_EDGE_LIMIT:-50000}" \
PYTHONPATH=src python3 src/scripts/research/build_signal_class_edge_scorecard_v1.py \
  | tee /tmp/signal_class_edge_scorecard_v1.log

grep -q "SIGNAL_CLASS_EDGE_SCORECARD_V1_OK" /tmp/signal_class_edge_scorecard_v1.log
grep -q "SIGNAL_CLASS_EDGE_SCORECARD_ROWS" /tmp/signal_class_edge_scorecard_v1.log
grep -q "SIGNAL_CLASS_EDGE_SCORECARD_SUMMARY" /tmp/signal_class_edge_scorecard_v1.log
grep -q "VERDICT=" /tmp/signal_class_edge_scorecard_v1.log

echo
echo "=== SIGNAL CLASS EDGE SCORECARD SUMMARY ==="
grep -E "SIGNAL_CLASS_EDGE_ROW|rows_total=|trades_total=|positive_rows=|negative_rows=|weak_rows=|commission_killed_rows=|open_tail_rows=|unclassified_rows=|total_net_pnl=|VERDICT=" \
  /tmp/signal_class_edge_scorecard_v1.log \
  | head -160

echo TEST_SIGNAL_CLASS_EDGE_SCORECARD_V1_OK
