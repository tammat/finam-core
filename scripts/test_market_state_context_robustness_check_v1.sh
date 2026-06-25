#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_MARKET_STATE_CONTEXT_ROBUSTNESS_CHECK_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_market_state_context_robustness_check_v1.py

src/scripts/research/build_market_state_context_robustness_check_v1.py \
  | tee /tmp/market_state_context_robustness_check_v1.out

grep -q "MARKET_STATE_CONTEXT_ROBUSTNESS_CHECK_V1" /tmp/market_state_context_robustness_check_v1.out
grep -q "DAILY_ROBUSTNESS" /tmp/market_state_context_robustness_check_v1.out
grep -q "SYMBOL_STRATEGY_BREAKDOWN" /tmp/market_state_context_robustness_check_v1.out
grep -q "days_total=" /tmp/market_state_context_robustness_check_v1.out
grep -q "positive_days=" /tmp/market_state_context_robustness_check_v1.out
grep -q "micro_live_candidates=0" /tmp/market_state_context_robustness_check_v1.out
grep -Eq "VERDICT=MARKET_STATE_CONTEXT_ROBUSTNESS_CANDIDATE_OK|VERDICT=MARKET_STATE_CONTEXT_ROBUSTNESS_WEAK" /tmp/market_state_context_robustness_check_v1.out

echo "TEST_MARKET_STATE_CONTEXT_ROBUSTNESS_CHECK_V1_OK"
