#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST SIGNAL CLASS EDGE SCORECARD V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/runtime/build_signal_class_edge_scorecard_v1.py

PYTHONPATH=src python3 src/scripts/runtime/build_signal_class_edge_scorecard_v1.py \
  | tee /tmp/signal_class_edge_scorecard_v1.log

grep -q "SIGNAL_CLASS_EDGE_SCORECARD_V1_OK" /tmp/signal_class_edge_scorecard_v1.log
grep -q "SIGNAL_CLASS_EDGE_SUMMARY" /tmp/signal_class_edge_scorecard_v1.log
grep -q "closed_cycles_total=" /tmp/signal_class_edge_scorecard_v1.log
grep -q "net_pnl_total=" /tmp/signal_class_edge_scorecard_v1.log
grep -q "VERDICT=" /tmp/signal_class_edge_scorecard_v1.log
grep -q "db_update=0" /tmp/signal_class_edge_scorecard_v1.log

echo
echo "=== SIGNAL CLASS EDGE SCORECARD SUMMARY ==="
grep -E "SIGNAL_CLASS_EDGE_ROW|closed_cycles_total=|gross_pnl_total=|commission_total=|net_pnl_total=|fee_drag_rows=|research_candidates=|VERDICT=" \
  /tmp/signal_class_edge_scorecard_v1.log

echo TEST_SIGNAL_CLASS_EDGE_SCORECARD_V1_OK
