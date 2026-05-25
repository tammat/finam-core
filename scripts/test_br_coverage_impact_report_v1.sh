#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/research/build_br_coverage_impact_report_v1.py

grep -q "BASELINE_FULL_CONTEXT" src/scripts/research/build_br_coverage_impact_report_v1.py
grep -q "FILTER_LOW_IMPULSE_DOWN_HIGH" src/scripts/research/build_br_coverage_impact_report_v1.py
grep -q "BR_COVERAGE_IMPACT_REPORT_V1_OK" src/scripts/research/build_br_coverage_impact_report_v1.py

echo "BR_COVERAGE_IMPACT_REPORT_V1_TEST_OK"
