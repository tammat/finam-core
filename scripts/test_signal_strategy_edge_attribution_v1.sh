#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST SIGNAL STRATEGY EDGE ATTRIBUTION V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/runtime/build_signal_strategy_edge_attribution_v1.py

PYTHONPATH=src python3 src/scripts/runtime/build_signal_strategy_edge_attribution_v1.py \
  | tee /tmp/signal_strategy_edge_attribution_v1.log

grep -q "SIGNAL_STRATEGY_EDGE_ATTRIBUTION_V1_OK" /tmp/signal_strategy_edge_attribution_v1.log
grep -q "SIGNAL_STRATEGY_ATTRIBUTION_SUMMARY" /tmp/signal_strategy_edge_attribution_v1.log
grep -q "trades_total=" /tmp/signal_strategy_edge_attribution_v1.log
grep -q "unknown_signal_rows=" /tmp/signal_strategy_edge_attribution_v1.log
grep -q "VERDICT=" /tmp/signal_strategy_edge_attribution_v1.log
grep -q "db_update=0" /tmp/signal_strategy_edge_attribution_v1.log

echo
echo "=== SIGNAL STRATEGY EDGE ATTRIBUTION SUMMARY ==="
grep -E "SIGNAL_STRATEGY_ATTRIBUTION_ROW|rows=|trades_total=|unknown_signal_rows=|fee_drag_signal_rows=|research_candidates=|VERDICT=" \
  /tmp/signal_strategy_edge_attribution_v1.log

echo TEST_SIGNAL_STRATEGY_EDGE_ATTRIBUTION_V1_OK
