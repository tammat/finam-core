#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_EDGE_VALIDATION_V2_START"

python -m py_compile src/scripts/analytics/build_edge_validation_v2.py

python src/scripts/analytics/build_edge_validation_v2.py \
  --limit 200 | tee /tmp/edge_validation_v2.out

grep -q "EDGE_VALIDATION_V2" /tmp/edge_validation_v2.out
grep -q "EDGE_VALIDATION_V2_ROW" /tmp/edge_validation_v2.out
grep -q "EDGE_VALIDATION_V2_SUMMARY" /tmp/edge_validation_v2.out
grep -q "EDGE_VALIDATION_V2_OK" /tmp/edge_validation_v2.out

echo "TEST_EDGE_VALIDATION_V2_OK"
