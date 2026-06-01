#!/usr/bin/env bash
set -euo pipefail

echo "TEST_BR_REGIME_CANDIDATE_VALIDATOR_V1_START"

python3 src/scripts/analytics/build_br_regime_candidate_validator_v1.py \
  --symbol BRM6@RTSX \
  --timeframe M5 \
  --lookback 20 \
  --horizons 3,6,12,24 \
  | grep -E "BR_REGIME_CANDIDATE_VALIDATOR_V1|BR_REGIME_CANDIDATE_ROW|BR_REGIME_CANDIDATE_SUMMARY|BR_REGIME_CANDIDATE_VALIDATOR_V1_OK"

echo "TEST_BR_REGIME_CANDIDATE_VALIDATOR_V1_OK"
