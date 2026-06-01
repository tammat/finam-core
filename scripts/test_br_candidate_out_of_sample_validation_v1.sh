#!/usr/bin/env bash
set -euo pipefail

echo "TEST_BR_CANDIDATE_OUT_OF_SAMPLE_VALIDATION_V1_START"

python3 src/scripts/analytics/build_br_candidate_out_of_sample_validation_v1.py \
  --symbol BRM6@RTSX \
  --timeframe M5 \
  --lookback 20 \
  --horizon 24 \
  --train-from 2026-04-01 \
  --train-to 2026-05-19 \
  --test-from 2026-05-20 \
  | grep -E "BR_CANDIDATE_OOS_VALIDATION_V1|BR_CANDIDATE_OOS_ROW|BR_CANDIDATE_OOS_COMPARISON|BR_CANDIDATE_OOS_FINAL|BR_CANDIDATE_OOS_VALIDATION_V1_OK"

echo "TEST_BR_CANDIDATE_OUT_OF_SAMPLE_VALIDATION_V1_OK"
