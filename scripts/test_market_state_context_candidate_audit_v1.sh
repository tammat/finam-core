#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_MARKET_STATE_CONTEXT_CANDIDATE_AUDIT_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_market_state_context_candidate_audit_v1.py

src/scripts/research/build_market_state_context_candidate_audit_v1.py \
  | tee /tmp/market_state_context_candidate_audit_v1.out

grep -q "MARKET_STATE_CONTEXT_CANDIDATE_AUDIT_V1" /tmp/market_state_context_candidate_audit_v1.out
grep -q "CANDIDATE_SUMMARY" /tmp/market_state_context_candidate_audit_v1.out
grep -q "trades=77" /tmp/market_state_context_candidate_audit_v1.out
grep -q "CANDIDATE_TRADES" /tmp/market_state_context_candidate_audit_v1.out
grep -q "VERDICT=MARKET_STATE_CONTEXT_CANDIDATE_AUDIT_READY" /tmp/market_state_context_candidate_audit_v1.out

echo "TEST_MARKET_STATE_CONTEXT_CANDIDATE_AUDIT_V1_OK"
