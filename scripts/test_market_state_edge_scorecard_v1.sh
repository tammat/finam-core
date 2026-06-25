#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_MARKET_STATE_EDGE_SCORECARD_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_market_state_edge_scorecard_v1.py

src/scripts/research/build_market_state_edge_scorecard_v1.py \
  | tee /tmp/market_state_edge_scorecard_v1.out

grep -q "MARKET_STATE_EDGE_SCORECARD_V1" /tmp/market_state_edge_scorecard_v1.out
grep -q "SCORECARD_ROWS" /tmp/market_state_edge_scorecard_v1.out
grep -q "rows_total=" /tmp/market_state_edge_scorecard_v1.out
grep -q "ready_for_pnl_linking=" /tmp/market_state_edge_scorecard_v1.out
grep -q "edge_candidates=0" /tmp/market_state_edge_scorecard_v1.out
grep -q "rule=no_pnl_until_trade_state_linking" /tmp/market_state_edge_scorecard_v1.out
grep -q "VERDICT=MARKET_STATE_EDGE_SCORECARD_READY" /tmp/market_state_edge_scorecard_v1.out

echo "TEST_MARKET_STATE_EDGE_SCORECARD_V1_OK"
