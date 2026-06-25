#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_HISTORICAL_MARKET_STATE_PNL_SCORECARD_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_historical_market_state_pnl_scorecard_v1.py

src/scripts/research/build_historical_market_state_pnl_scorecard_v1.py \
  | tee /tmp/historical_market_state_pnl_scorecard_v1.out

grep -q "HISTORICAL_MARKET_STATE_PNL_SCORECARD_V1" /tmp/historical_market_state_pnl_scorecard_v1.out
grep -q "HISTORICAL_PNL_ROWS" /tmp/historical_market_state_pnl_scorecard_v1.out
grep -q "rows_total=" /tmp/historical_market_state_pnl_scorecard_v1.out
grep -q "research_candidates=" /tmp/historical_market_state_pnl_scorecard_v1.out
grep -q "next=MARKET_INDEX_STATE_CONTEXT_PLAN_V1" /tmp/historical_market_state_pnl_scorecard_v1.out
grep -q "VERDICT=HISTORICAL_MARKET_STATE_PNL_SCORECARD_READY" /tmp/historical_market_state_pnl_scorecard_v1.out

echo "TEST_HISTORICAL_MARKET_STATE_PNL_SCORECARD_V1_OK"
