#!/usr/bin/env bash
set -euo pipefail

echo "TEST_BR_CANDIDATES_OOS_VALIDATION_V2_START"

python3 src/scripts/analytics/build_br_candidates_out_of_sample_validation_v2.py \
  --symbol BRM6@RTSX \
  --timeframe M5 \
  --lookback 20 \
  --horizons 6,12,24 \
  --train-from 2026-04-01 \
  --train-to 2026-05-19 \
  --test-from 2026-05-20 \
  | grep -E "BR_CANDIDATES_OOS_VALIDATION_V2|BR_CANDIDATES_OOS_ROW|BR_CANDIDATES_OOS_FINAL|BR_CANDIDATES_OOS_VALIDATION_V2_OK"

echo "TEST_BR_CANDIDATES_OOS_VALIDATION_V2_OK"
