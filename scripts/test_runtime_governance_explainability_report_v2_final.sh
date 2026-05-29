#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src
export WINDOW_HOURS=168

echo "TEST_RUNTIME_GOVERNANCE_EXPLAINABILITY_REPORT_V2_FINAL_START"

python -m py_compile src/scripts/analytics/build_runtime_governance_explainability_v1.py

python src/scripts/analytics/build_runtime_governance_explainability_v1.py \
  | tee /tmp/runtime_governance_explainability_report_v2_final_test.out

grep -q "вердикт=" /tmp/runtime_governance_explainability_report_v2_final_test.out
grep -q "человеческое_объяснение=" /tmp/runtime_governance_explainability_report_v2_final_test.out
grep -q "источник_решения=" /tmp/runtime_governance_explainability_report_v2_final_test.out
grep -q "RUNTIME_GOVERNANCE_EXPLAINABILITY_V1_OK" /tmp/runtime_governance_explainability_report_v2_final_test.out

echo "TEST_RUNTIME_GOVERNANCE_EXPLAINABILITY_REPORT_V2_FINAL_OK"
