#!/usr/bin/env bash
set -euo pipefail

echo "TEST_BR_CANDIDATE_REPLAY_FILTER_V1_START"

python3 src/scripts/analytics/build_br_candidate_replay_filter_v1.py \
  --symbol BRM6@RTSX \
  --timeframe M5 \
  --lookback 20 \
  --horizon 24 \
  | grep -E "BR_CANDIDATE_REPLAY_FILTER_V1|BR_CANDIDATE_REPLAY_ROW|BR_CANDIDATE_REPLAY_SUMMARY|BR_CANDIDATE_REPLAY_FILTER_V1_OK"

echo "TEST_BR_CANDIDATE_REPLAY_FILTER_V1_OK"
