#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_EDGE_CANDIDATE_DISCOVERY_FROM_EXISTING_SCORECARDS_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_edge_candidate_discovery_from_existing_scorecards_v1.py

src/scripts/research/build_edge_candidate_discovery_from_existing_scorecards_v1.py \
  | tee /tmp/edge_candidate_discovery_from_existing_scorecards_v1.out

grep -q "EDGE_CANDIDATE_DISCOVERY_FROM_EXISTING_SCORECARDS_V1" /tmp/edge_candidate_discovery_from_existing_scorecards_v1.out
grep -q "real_trading_enabled=0" /tmp/edge_candidate_discovery_from_existing_scorecards_v1.out
grep -q "orders_sent=0" /tmp/edge_candidate_discovery_from_existing_scorecards_v1.out
grep -q "SOURCE name=clean_runtime_signal_class_edge_scorecard_v1" /tmp/edge_candidate_discovery_from_existing_scorecards_v1.out
grep -q "FILTER name=use_clean_runtime_or_paper_only_for_micro_live" /tmp/edge_candidate_discovery_from_existing_scorecards_v1.out
grep -q "FINDING name=br_historical_replay status=RESEARCH_ONLY" /tmp/edge_candidate_discovery_from_existing_scorecards_v1.out
grep -q "eligible_micro_live_candidates=0" /tmp/edge_candidate_discovery_from_existing_scorecards_v1.out
grep -q "selected_candidate=NONE" /tmp/edge_candidate_discovery_from_existing_scorecards_v1.out
grep -q "rule=discovery_script_cannot_enable_runtime" /tmp/edge_candidate_discovery_from_existing_scorecards_v1.out
grep -q "VERDICT=EDGE_CANDIDATE_DISCOVERY_NO_MICRO_LIVE_CANDIDATE" /tmp/edge_candidate_discovery_from_existing_scorecards_v1.out

echo "TEST_EDGE_CANDIDATE_DISCOVERY_FROM_EXISTING_SCORECARDS_V1_OK"
