#!/usr/bin/env bash
set -euo pipefail

echo "TEST_BR_REGIME_CANDIDATE_VALIDATOR_V2_START"

python3 src/scripts/analytics/build_br_regime_candidate_validator_v2.py \
  --symbol BRM6@RTSX \
  --timeframe M5 \
  --lookback 20 \
  --horizons 3,6,12,24 \
  | grep -E "BR_REGIME_CANDIDATE_VALIDATOR_V2|BR_REGIME_CANDIDATE_V2_ROW|BR_REGIME_CANDIDATE_V2_SUMMARY|BR_REGIME_CANDIDATE_VALIDATOR_V2_OK"

echo "TEST_BR_REGIME_CANDIDATE_VALIDATOR_V2_OK"
