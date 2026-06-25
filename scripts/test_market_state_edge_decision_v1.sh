#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_MARKET_STATE_EDGE_DECISION_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_market_state_edge_decision_v1.py

src/scripts/research/build_market_state_edge_decision_v1.py \
  | tee /tmp/market_state_edge_decision_v1.out

grep -q "MARKET_STATE_EDGE_DECISION_V1" /tmp/market_state_edge_decision_v1.out
grep -q "positive_rows=6" /tmp/market_state_edge_decision_v1.out
grep -q "research_candidates=0" /tmp/market_state_edge_decision_v1.out
grep -q "micro_live_candidates=0" /tmp/market_state_edge_decision_v1.out
grep -q "decision=DO_NOT_PROMOTE_TO_MICRO_LIVE" /tmp/market_state_edge_decision_v1.out
grep -q "reason=sample_size_below_30_trades_per_state" /tmp/market_state_edge_decision_v1.out
grep -q "next=MARKET_STATE_COMMISSION_SOURCE_AUDIT_V1" /tmp/market_state_edge_decision_v1.out
grep -q "VERDICT=MARKET_STATE_EDGE_DECISION_NO_PROMOTION_CONTINUE_RESEARCH" /tmp/market_state_edge_decision_v1.out

echo "TEST_MARKET_STATE_EDGE_DECISION_V1_OK"
