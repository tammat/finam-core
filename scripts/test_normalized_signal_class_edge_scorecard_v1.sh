#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST NORMALIZED SIGNAL CLASS EDGE SCORECARD V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/research/build_normalized_signal_class_edge_scorecard_v1.py

PYTHONPATH=src python3 src/scripts/research/build_normalized_signal_class_edge_scorecard_v1.py \
  | tee /tmp/normalized_signal_class_edge_scorecard_v1.log

grep -q "NORMALIZED_SIGNAL_CLASS_EDGE_SCORECARD_V1_OK" /tmp/normalized_signal_class_edge_scorecard_v1.log
grep -q "NORMALIZED_SIGNAL_CLASS_EDGE_SCORECARD_SUMMARY" /tmp/normalized_signal_class_edge_scorecard_v1.log
grep -q "trades_with_signal_class=" /tmp/normalized_signal_class_edge_scorecard_v1.log
grep -q "unknown_review_rows=" /tmp/normalized_signal_class_edge_scorecard_v1.log
grep -q "closed_cycles_total=" /tmp/normalized_signal_class_edge_scorecard_v1.log
grep -q "research_candidates=" /tmp/normalized_signal_class_edge_scorecard_v1.log
grep -q "historical_research_candidates=" /tmp/normalized_signal_class_edge_scorecard_v1.log
grep -q "dirty_data_review_rows=" /tmp/normalized_signal_class_edge_scorecard_v1.log
grep -q "VERDICT=" /tmp/normalized_signal_class_edge_scorecard_v1.log
grep -q "db_update=0" /tmp/normalized_signal_class_edge_scorecard_v1.log

echo
echo "=== NORMALIZED SIGNAL CLASS EDGE SCORECARD SUMMARY ==="
grep -E "NORMALIZED_SIGNAL_CLASS_EDGE_ROW|trades_with_signal_class=|unknown_review_rows=|closed_cycles_total=|groups_total=|research_candidates=|historical_research_candidates=|dirty_data_review_rows=|rejected_negative_rows=|fee_drag_rows=|insufficient_data_rows=|net_pnl_total=|commission_total=|VERDICT=" \
  /tmp/normalized_signal_class_edge_scorecard_v1.log | head -120

echo TEST_NORMALIZED_SIGNAL_CLASS_EDGE_SCORECARD_V1_OK
