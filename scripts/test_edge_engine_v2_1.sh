#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_EDGE_ENGINE_V2_1_START"

python -m py_compile src/scripts/analytics/build_edge_engine_v2_1.py

python src/scripts/analytics/build_edge_engine_v2_1.py \
  --min-trades 5 \
  --min-pf 1.20 \
  --min-expectancy 0.0 | tee /tmp/edge_engine_v2_1.out

grep -q "EDGE_ENGINE_V2_1" /tmp/edge_engine_v2_1.out
grep -q "EDGE_ENGINE_V2_1_ROW" /tmp/edge_engine_v2_1.out
grep -q "EDGE_ENGINE_V2_1_SUMMARY" /tmp/edge_engine_v2_1.out
grep -q "EDGE_ENGINE_V2_1_OK" /tmp/edge_engine_v2_1.out

echo "TEST_EDGE_ENGINE_V2_1_OK"
