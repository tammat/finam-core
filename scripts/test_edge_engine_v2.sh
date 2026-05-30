#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_EDGE_ENGINE_V2_START"

python -m py_compile src/scripts/analytics/build_edge_engine_v2.py

python src/scripts/analytics/build_edge_engine_v2.py \
  --min-trades 30 \
  --min-pf 1.20 \
  --min-expectancy 0.0 | tee /tmp/edge_engine_v2.out

grep -q "EDGE_ENGINE_V2" /tmp/edge_engine_v2.out
grep -q "EDGE_ENGINE_V2_ROW" /tmp/edge_engine_v2.out
grep -q "EDGE_ENGINE_V2_SUMMARY" /tmp/edge_engine_v2.out
grep -q "EDGE_ENGINE_V2_OK" /tmp/edge_engine_v2.out

echo "TEST_EDGE_ENGINE_V2_OK"
