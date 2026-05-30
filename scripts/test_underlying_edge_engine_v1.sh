#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_UNDERLYING_EDGE_ENGINE_V1_START"

python -m py_compile src/scripts/analytics/build_underlying_edge_engine_v1.py

python src/scripts/analytics/build_underlying_edge_engine_v1.py \
  --min-trades 50 \
  --min-pf 1.30 \
  --min-expectancy 0.0 | tee /tmp/underlying_edge_engine_v1.out

grep -q "UNDERLYING_EDGE_ENGINE_V1" /tmp/underlying_edge_engine_v1.out
grep -q "UNDERLYING_EDGE_ENGINE_V1_ROW" /tmp/underlying_edge_engine_v1.out
grep -q "UNDERLYING_EDGE_ENGINE_V1_SUMMARY" /tmp/underlying_edge_engine_v1.out
grep -q "UNDERLYING_EDGE_ENGINE_V1_OK" /tmp/underlying_edge_engine_v1.out

echo "TEST_UNDERLYING_EDGE_ENGINE_V1_OK"
