#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_BR_HISTORICAL_EDGE_V1_START"

python -m py_compile src/scripts/analytics/build_br_historical_edge_v1.py

python src/scripts/analytics/build_br_historical_edge_v1.py \
  --symbols BRM6@RTSX \
  --timeframe M5 \
  --lookback 20 \
  --horizons 12,24,48 \
  > /tmp/br_edge.out

grep -q "BR_EDGE_TOTAL" /tmp/br_edge.out
grep -q "BR_EDGE_SYMBOL" /tmp/br_edge.out
grep -q "BR_HISTORICAL_EDGE_V1_OK" /tmp/br_edge.out

echo "TEST_BR_HISTORICAL_EDGE_V1_OK"
