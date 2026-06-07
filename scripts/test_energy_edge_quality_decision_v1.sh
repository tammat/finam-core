#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

python3 -m py_compile src/scripts/analytics/build_energy_edge_quality_decision_v1.py

python3 src/scripts/analytics/build_energy_edge_quality_decision_v1.py | \
  tee /tmp/energy_edge_quality_decision_v1.log

grep -q "ENERGY EDGE QUALITY DECISION V1" /tmp/energy_edge_quality_decision_v1.log
grep -q "DIRECTION_DECISIONS" /tmp/energy_edge_quality_decision_v1.log
grep -q "RUNTIME_POLICY_MATRIX" /tmp/energy_edge_quality_decision_v1.log
grep -q "ENERGY_EDGE_QUALITY_DECISION_V1_OK" /tmp/energy_edge_quality_decision_v1.log

echo TEST_ENERGY_EDGE_QUALITY_DECISION_V1_OK
