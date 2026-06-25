#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_RESEARCH_MARKET_STATE_ENGINE_ARCHITECTURE_REVIEW_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_research_market_state_engine_architecture_review_v1.py

src/scripts/research/build_research_market_state_engine_architecture_review_v1.py \
  | tee /tmp/research_market_state_engine_architecture_review_v1.out

grep -q "RESEARCH_MARKET_STATE_ENGINE_ARCHITECTURE_REVIEW_V1" /tmp/research_market_state_engine_architecture_review_v1.out
grep -q "mode=review_only" /tmp/research_market_state_engine_architecture_review_v1.out
grep -q "CHECK name=engine_is_research_only status=PASS" /tmp/research_market_state_engine_architecture_review_v1.out
grep -q "CHECK name=engine_is_pnl_blind status=PASS" /tmp/research_market_state_engine_architecture_review_v1.out
grep -q "CHECK name=engine_is_trade_result_blind status=PASS" /tmp/research_market_state_engine_architecture_review_v1.out
grep -q "CHECK name=engine_does_not_send_orders status=PASS" /tmp/research_market_state_engine_architecture_review_v1.out
grep -q "CHECK name=engine_never_makes_buy_sell_hold_decision status=PASS" /tmp/research_market_state_engine_architecture_review_v1.out
grep -q "CHECK name=snapshots_are_immutable status=PASS" /tmp/research_market_state_engine_architecture_review_v1.out
grep -q "CHECK name=confidence_separated_from_quality status=PASS" /tmp/research_market_state_engine_architecture_review_v1.out
grep -q "CHECK name=canonical_signature_required status=PASS" /tmp/research_market_state_engine_architecture_review_v1.out
grep -q "CHECK name=compact_signature_required status=PASS" /tmp/research_market_state_engine_architecture_review_v1.out
grep -q "blocker_count=0" /tmp/research_market_state_engine_architecture_review_v1.out
grep -q "VERDICT=RESEARCH_MARKET_STATE_ENGINE_ARCHITECTURE_REVIEW_APPROVED" /tmp/research_market_state_engine_architecture_review_v1.out

echo "TEST_RESEARCH_MARKET_STATE_ENGINE_ARCHITECTURE_REVIEW_V1_OK"
