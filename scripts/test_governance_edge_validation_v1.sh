#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_GOVERNANCE_EDGE_VALIDATION_V1_START"

python -m py_compile src/scripts/analytics/build_governance_edge_validation_v1.py

python src/scripts/analytics/build_governance_edge_validation_v1.py \
  > /tmp/governance_edge_validation.out

grep -q "GOVERNANCE_EDGE_VALIDATION_V1" /tmp/governance_edge_validation.out
grep -q "GOVERNANCE_EDGE_VALIDATION_SUMMARY" /tmp/governance_edge_validation.out
grep -q "GOVERNANCE_EDGE_SYMBOL" /tmp/governance_edge_validation.out
grep -q "GOVERNANCE_EDGE_REASON" /tmp/governance_edge_validation.out
grep -q "GOVERNANCE_EDGE_VALIDATION_V1_OK" /tmp/governance_edge_validation.out

echo "TEST_GOVERNANCE_EDGE_VALIDATION_V1_OK"
