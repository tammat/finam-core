#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

python3 -m py_compile src/scripts/analytics/build_energy_edge_quality_summary_v1.py

python3 src/scripts/analytics/build_energy_edge_quality_summary_v1.py | \
  tee /tmp/energy_edge_quality_summary_v1.log

grep -q "ENERGY EDGE QUALITY SUMMARY V1" /tmp/energy_edge_quality_summary_v1.log
grep -q "TRADE_SUMMARY_BY_ROOT_SIDE" /tmp/energy_edge_quality_summary_v1.log
grep -q "POLICY_STATUS" /tmp/energy_edge_quality_summary_v1.log
grep -q "ENERGY_EDGE_QUALITY_SUMMARY_V1_OK" /tmp/energy_edge_quality_summary_v1.log

echo TEST_ENERGY_EDGE_QUALITY_SUMMARY_V1_OK
