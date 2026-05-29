#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_RUNTIME_GOVERNANCE_EXPLAINABILITY_REPORT_V2_PAYLOAD_START"

python -m py_compile src/scripts/analytics/build_runtime_governance_explainability_v1.py

WINDOW_HOURS=168 python src/scripts/analytics/build_runtime_governance_explainability_v1.py \
  | tee /tmp/runtime_governance_explainability_report_v2_payload.out

grep -q "RUNTIME_GOVERNANCE_EXPLAINABILITY_V1_OK" /tmp/runtime_governance_explainability_report_v2_payload.out
grep -q "причина=" /tmp/runtime_governance_explainability_report_v2_payload.out
grep -q "уровень_уверенности=" /tmp/runtime_governance_explainability_report_v2_payload.out
grep -q "сила_преимущества=" /tmp/runtime_governance_explainability_report_v2_payload.out
grep -q "доказательства=" /tmp/runtime_governance_explainability_report_v2_payload.out

echo "TEST_RUNTIME_GOVERNANCE_EXPLAINABILITY_REPORT_V2_PAYLOAD_OK"
