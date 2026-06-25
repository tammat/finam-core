#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_MARKET_STATE_PNL_SCORECARD_V1_1 ==="

python3 -m py_compile \
  src/scripts/research/build_market_state_pnl_scorecard_v1_1.py

src/scripts/research/build_market_state_pnl_scorecard_v1_1.py \
  | tee /tmp/market_state_pnl_scorecard_v1_1.out

grep -q "MARKET_STATE_PNL_SCORECARD_V1_1" /tmp/market_state_pnl_scorecard_v1_1.out
grep -q "LINK_SUMMARY" /tmp/market_state_pnl_scorecard_v1_1.out
grep -q "PNL_SCORECARD_ROWS" /tmp/market_state_pnl_scorecard_v1_1.out
grep -q "link_ok=43" /tmp/market_state_pnl_scorecard_v1_1.out
grep -q "rows_total=" /tmp/market_state_pnl_scorecard_v1_1.out
grep -q "positive_rows=" /tmp/market_state_pnl_scorecard_v1_1.out
grep -q "research_candidates=" /tmp/market_state_pnl_scorecard_v1_1.out
grep -q "micro_live_candidates=0" /tmp/market_state_pnl_scorecard_v1_1.out
grep -Eq "VERDICT=MARKET_STATE_PNL_SCORECARD_V1_1_READY|VERDICT=MARKET_STATE_PNL_SCORECARD_V1_1_NO_LINKED_PNL_ROWS" /tmp/market_state_pnl_scorecard_v1_1.out

echo "TEST_MARKET_STATE_PNL_SCORECARD_V1_1_OK"
