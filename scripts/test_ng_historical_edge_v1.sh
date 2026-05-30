#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_NG_HISTORICAL_EDGE_V1_START"

python -m py_compile src/scripts/analytics/build_ng_historical_edge_v1.py

python src/scripts/analytics/build_ng_historical_edge_v1.py \
  > /tmp/ng_historical_edge_v1.out

grep -q "NG_HISTORICAL_EDGE_V1" /tmp/ng_historical_edge_v1.out
grep -q "NG_EDGE_CONFIG" /tmp/ng_historical_edge_v1.out
grep -q "NG_EDGE_TOTAL" /tmp/ng_historical_edge_v1.out
grep -q "NG_EDGE_SYMBOL" /tmp/ng_historical_edge_v1.out
grep -q "NG_HISTORICAL_EDGE_V1_OK" /tmp/ng_historical_edge_v1.out

echo "TEST_NG_HISTORICAL_EDGE_V1_OK"
