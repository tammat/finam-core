#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_GOVERNANCE_EDGE_VALIDATION_V1_1_START"

python -m py_compile src/scripts/analytics/build_governance_edge_validation_v1_1.py

python src/scripts/analytics/build_governance_edge_validation_v1_1.py \
  > /tmp/governance_edge_validation_v1_1.out

grep -q "GOVERNANCE_EDGE_VALIDATION_V1_1" /tmp/governance_edge_validation_v1_1.out
grep -q "GOVERNANCE_EDGE_SAMPLE_QUALITY" /tmp/governance_edge_validation_v1_1.out
grep -q "GOVERNANCE_EDGE_EFFICIENCY" /tmp/governance_edge_validation_v1_1.out
grep -q "GOVERNANCE_EDGE_SIDE" /tmp/governance_edge_validation_v1_1.out
grep -q "GOVERNANCE_EDGE_ALPHA_RANK" /tmp/governance_edge_validation_v1_1.out
grep -q "GOVERNANCE_EDGE_VALIDATION_V1_1_OK" /tmp/governance_edge_validation_v1_1.out

echo "TEST_GOVERNANCE_EDGE_VALIDATION_V1_1_OK"
