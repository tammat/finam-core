#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_USD_HISTORICAL_EDGE_V1_START"

python -m py_compile src/scripts/analytics/build_usd_historical_edge_v1.py

python src/scripts/analytics/build_usd_historical_edge_v1.py \
  > /tmp/usd_historical_edge_v1.out

grep -q "USD_HISTORICAL_EDGE_V1" /tmp/usd_historical_edge_v1.out
grep -q "USD_EDGE_CONFIG" /tmp/usd_historical_edge_v1.out
grep -q "USD_EDGE_TOTAL" /tmp/usd_historical_edge_v1.out
grep -q "USD_EDGE_SYMBOL" /tmp/usd_historical_edge_v1.out
grep -q "USD_HISTORICAL_EDGE_V1_OK" /tmp/usd_historical_edge_v1.out

echo "TEST_USD_HISTORICAL_EDGE_V1_OK"
