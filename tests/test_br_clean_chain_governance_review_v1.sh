#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST BR CLEAN CHAIN GOVERNANCE REVIEW V1 ==="

python -m py_compile \
  src/scripts/research/build_br_clean_chain_governance_review_v1.py

OUTPUT="$(
    PYTHONPATH=src \
    python src/scripts/research/build_br_clean_chain_governance_review_v1.py
)"

echo "$OUTPUT"

grep -q 'source=closed_trade_chains_v3' <<< "$OUTPUT"
grep -q 'quality_status=FULL' <<< "$OUTPUT"

grep -q \
  'research_decision=REJECT_CURRENT_BR_STRATEGY' \
  <<< "$OUTPUT"

grep -q \
  'reason=negative_clean_full_chain_edge' \
  <<< "$OUTPUT"

grep -q 'db_writes_performed=0' <<< "$OUTPUT"
grep -q 'runtime_changed=0' <<< "$OUTPUT"
grep -q 'execution_changed=0' <<< "$OUTPUT"
grep -q 'runtime_allow=0' <<< "$OUTPUT"
grep -q 'execution_enabled=0' <<< "$OUTPUT"

grep -q \
'VERDICT=BR_CLEAN_CHAIN_GOVERNANCE_REVIEW_V1_REJECT_CURRENT_BR_STRATEGY' \
<<< "$OUTPUT"

echo
echo "=== DIFF CHECK ==="
git diff --check

echo
echo "VERDICT=TEST_BR_CLEAN_CHAIN_GOVERNANCE_REVIEW_V1_OK"
