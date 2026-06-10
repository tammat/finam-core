#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/research/build_gold_replay_v2_final_candidate_summary.py

python3 src/scripts/research/build_gold_replay_v2_final_candidate_summary.py \
  | tee /tmp/gold_replay_v2_final_candidate_summary.log

grep -q "GOLD REPLAY V2 FINAL CANDIDATE SUMMARY" \
  /tmp/gold_replay_v2_final_candidate_summary.log

grep -q "FINAL_PROFILE" \
  /tmp/gold_replay_v2_final_candidate_summary.log

grep -q "FINAL_VERDICT" \
  /tmp/gold_replay_v2_final_candidate_summary.log

grep -q "GOLD_REPLAY_V2_FINAL_CANDIDATE_SUMMARY_OK" \
  /tmp/gold_replay_v2_final_candidate_summary.log

echo TEST_GOLD_REPLAY_V2_FINAL_CANDIDATE_SUMMARY_OK
