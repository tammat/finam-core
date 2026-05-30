#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_EDGE_VALIDATION_V3_START"

python -m py_compile src/scripts/analytics/build_edge_validation_v3.py

python src/scripts/analytics/build_edge_validation_v3.py \
  --limit 200 | tee /tmp/edge_validation_v3.out

grep -q "EDGE_VALIDATION_V3" /tmp/edge_validation_v3.out
grep -q "EDGE_VALIDATION_V3_ROW" /tmp/edge_validation_v3.out
grep -q "EDGE_VALIDATION_V3_SUMMARY" /tmp/edge_validation_v3.out
grep -q "EDGE_VALIDATION_V3_OK" /tmp/edge_validation_v3.out

echo "TEST_EDGE_VALIDATION_V3_OK"
