#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_MARKET_STATE_CONTEXT_SCORECARD_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_market_state_context_scorecard_v1.py

src/scripts/research/build_market_state_context_scorecard_v1.py \
  | tee /tmp/market_state_context_scorecard_v1.out

grep -q "MARKET_STATE_CONTEXT_SCORECARD_V1" /tmp/market_state_context_scorecard_v1.out
grep -q "CONTEXT_SCORECARD_ROWS" /tmp/market_state_context_scorecard_v1.out
grep -q "context_links=" /tmp/market_state_context_scorecard_v1.out
grep -q "rows_total=" /tmp/market_state_context_scorecard_v1.out
grep -q "positive_rows=" /tmp/market_state_context_scorecard_v1.out
grep -q "research_candidates=" /tmp/market_state_context_scorecard_v1.out
grep -q "micro_live_candidates=0" /tmp/market_state_context_scorecard_v1.out
grep -q "VERDICT=MARKET_STATE_CONTEXT_SCORECARD_READY" /tmp/market_state_context_scorecard_v1.out

echo "TEST_MARKET_STATE_CONTEXT_SCORECARD_V1_OK"
