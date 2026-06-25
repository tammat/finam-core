#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_EDGE_CANDIDATE_SELECTION_FOR_MICRO_LIVE_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_edge_candidate_selection_for_micro_live_v1.py

src/scripts/research/build_edge_candidate_selection_for_micro_live_v1.py \
  | tee /tmp/edge_candidate_selection_for_micro_live_v1.out

grep -q "EDGE_CANDIDATE_SELECTION_FOR_MICRO_LIVE_V1" /tmp/edge_candidate_selection_for_micro_live_v1.out
grep -q "real_trading_enabled=0" /tmp/edge_candidate_selection_for_micro_live_v1.out
grep -q "orders_sent=0" /tmp/edge_candidate_selection_for_micro_live_v1.out
grep -q "CRITERION name=expectancy_positive_after_commission" /tmp/edge_candidate_selection_for_micro_live_v1.out
grep -q "SOURCE name=research.state_edge_scorecards_v1" /tmp/edge_candidate_selection_for_micro_live_v1.out
grep -q "BLOCKER name=NO_CONFIRMED_EDGE_CANDIDATE_YET" /tmp/edge_candidate_selection_for_micro_live_v1.out
grep -q "eligible_candidates=0" /tmp/edge_candidate_selection_for_micro_live_v1.out
grep -q "selected_candidate=NONE" /tmp/edge_candidate_selection_for_micro_live_v1.out
grep -q "rule=selection_script_cannot_enable_runtime" /tmp/edge_candidate_selection_for_micro_live_v1.out
grep -q "VERDICT=EDGE_CANDIDATE_SELECTION_NO_ELIGIBLE_CANDIDATE_NOT_ENABLED" /tmp/edge_candidate_selection_for_micro_live_v1.out

echo "TEST_EDGE_CANDIDATE_SELECTION_FOR_MICRO_LIVE_V1_OK"
