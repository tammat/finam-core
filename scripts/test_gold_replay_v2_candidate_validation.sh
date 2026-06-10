#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/research/build_gold_replay_v2_candidate_validation.py

python3 src/scripts/research/build_gold_replay_v2_candidate_validation.py \
  | tee /tmp/gold_replay_v2_candidate_validation.log

grep -q "GOLD REPLAY V2 CANDIDATE VALIDATION" /tmp/gold_replay_v2_candidate_validation.log
grep -q "CONFIG_ROW" /tmp/gold_replay_v2_candidate_validation.log
grep -q "RESULT_ROW" /tmp/gold_replay_v2_candidate_validation.log
grep -q "VERDICT=" /tmp/gold_replay_v2_candidate_validation.log
grep -q "GOLD_REPLAY_V2_CANDIDATE_VALIDATION_OK" /tmp/gold_replay_v2_candidate_validation.log

echo "TEST_GOLD_REPLAY_V2_CANDIDATE_VALIDATION_OK"
