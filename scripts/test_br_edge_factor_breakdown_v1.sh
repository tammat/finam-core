#!/usr/bin/env bash
set -euo pipefail

echo "TEST_BR_EDGE_FACTOR_BREAKDOWN_V1_START"

python3 src/scripts/analytics/build_br_edge_factor_breakdown_v1.py \
  --symbol BRM6@RTSX \
  --timeframe M5 \
  --lookback 20 \
  --horizons 3,6,12,24 \
  | grep -E "BR_EDGE_FACTOR_BREAKDOWN_V1|BR_EDGE_FACTOR_ROW|BR_EDGE_FACTOR_SUMMARY|BR_EDGE_FACTOR_BREAKDOWN_V1_OK"

echo "TEST_BR_EDGE_FACTOR_BREAKDOWN_V1_OK"
