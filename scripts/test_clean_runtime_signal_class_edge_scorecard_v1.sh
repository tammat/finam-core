#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST CLEAN RUNTIME SIGNAL CLASS EDGE SCORECARD V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/research/build_clean_runtime_signal_class_edge_scorecard_v1.py

PYTHONPATH=src python3 src/scripts/research/build_clean_runtime_signal_class_edge_scorecard_v1.py \
  | tee /tmp/clean_runtime_signal_class_edge_scorecard_v1.log

grep -q "CLEAN_RUNTIME_SIGNAL_CLASS_EDGE_SCORECARD_V1_OK" /tmp/clean_runtime_signal_class_edge_scorecard_v1.log
grep -q "CLEAN_RUNTIME_SIGNAL_CLASS_EDGE_SCORECARD_SUMMARY" /tmp/clean_runtime_signal_class_edge_scorecard_v1.log
grep -q "trades_clean_runtime_or_paper=688" /tmp/clean_runtime_signal_class_edge_scorecard_v1.log
grep -q "clean_research_candidates=" /tmp/clean_runtime_signal_class_edge_scorecard_v1.log
grep -q "rejected_negative_rows=" /tmp/clean_runtime_signal_class_edge_scorecard_v1.log
grep -q "VERDICT=" /tmp/clean_runtime_signal_class_edge_scorecard_v1.log
grep -q "db_update=0" /tmp/clean_runtime_signal_class_edge_scorecard_v1.log

echo
echo "=== CLEAN RUNTIME SIGNAL CLASS EDGE SUMMARY ==="
grep -E "CLEAN_RUNTIME_SIGNAL_CLASS_EDGE_ROW|trades_clean_runtime_or_paper=|closed_cycles_total=|groups_total=|clean_research_candidates=|rejected_negative_rows=|fee_drag_rows=|insufficient_data_rows=|net_pnl_total=|commission_total=|VERDICT=" \
  /tmp/clean_runtime_signal_class_edge_scorecard_v1.log | head -120

echo TEST_CLEAN_RUNTIME_SIGNAL_CLASS_EDGE_SCORECARD_V1_OK
