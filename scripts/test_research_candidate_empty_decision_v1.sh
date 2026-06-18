#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST RESEARCH CANDIDATE EMPTY DECISION V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile \
  src/scripts/research/build_signal_class_strategy_candidate_plan_v1.py \
  src/scripts/research/build_smart_entry_retest_quarantine_apply_plan_review_v1.py \
  src/scripts/research/build_research_candidate_empty_decision_v1.py

PYTHONPATH=src python3 src/scripts/research/build_research_candidate_empty_decision_v1.py \
  | tee /tmp/research_candidate_empty_decision_v1.log

grep -q "RESEARCH_CANDIDATE_EMPTY_DECISION_V1_OK" /tmp/research_candidate_empty_decision_v1.log
grep -q "RESEARCH_CANDIDATE_EMPTY_DECISION_CHECKS" /tmp/research_candidate_empty_decision_v1.log
grep -q "RESEARCH_CANDIDATE_EMPTY_DECISION_SUMMARY" /tmp/research_candidate_empty_decision_v1.log
grep -q "promote_to_research_candidate=0" /tmp/research_candidate_empty_decision_v1.log
grep -q "gold_confirmed=0" /tmp/research_candidate_empty_decision_v1.log
grep -q "smart_retest_apply_candidates=0" /tmp/research_candidate_empty_decision_v1.log
grep -q "runtime_changes_required=0" /tmp/research_candidate_empty_decision_v1.log
grep -q "execution_changes_required=0" /tmp/research_candidate_empty_decision_v1.log
grep -q "VERDICT=RESEARCH_CANDIDATE_EMPTY_DECISION_CONFIRMED" /tmp/research_candidate_empty_decision_v1.log

if grep -q "status=FAIL" /tmp/research_candidate_empty_decision_v1.log; then
  echo "FAIL: research candidate decision has failed checks"
  exit 1
fi

echo
echo "=== RESEARCH CANDIDATE EMPTY DECISION SUMMARY ==="
grep -E "RESEARCH_CANDIDATE_EMPTY_DECISION_CHECK|checks_total=|checks_failed=|promote_to_research_candidate=|gold_confirmed=|smart_retest_apply_candidates=|new_strategy_candidates=|runtime_changes_required=|execution_changes_required=|decision=|VERDICT=" \
  /tmp/research_candidate_empty_decision_v1.log

echo TEST_RESEARCH_CANDIDATE_EMPTY_DECISION_V1_OK
