#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_BR_EDGE_VALIDATION_V1_START"

python -m py_compile src/scripts/analytics/build_br_edge_validation_v1.py

python src/scripts/analytics/build_br_edge_validation_v1.py \
  --window-days 30 \
  --outlier-pct 0.20 | tee /tmp/br_edge_validation_v1.out

grep -q "BR_EDGE_TOTAL" /tmp/br_edge_validation_v1.out
grep -q "BR_EDGE_OUTLIER" /tmp/br_edge_validation_v1.out
grep -q "BR_EDGE_CLEAN_TOTAL" /tmp/br_edge_validation_v1.out
grep -q "BR_EDGE_VERDICT" /tmp/br_edge_validation_v1.out
grep -q "BR_EDGE_VALIDATION_V1_OK" /tmp/br_edge_validation_v1.out

echo "TEST_BR_EDGE_VALIDATION_V1_OK"
