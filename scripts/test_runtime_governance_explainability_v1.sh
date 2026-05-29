#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_RUNTIME_GOVERNANCE_EXPLAINABILITY_V1_START"

python -m py_compile src/scripts/analytics/build_runtime_governance_explainability_v1.py

WINDOW_HOURS=168 python src/scripts/analytics/build_runtime_governance_explainability_v1.py | tee /tmp/runtime_governance_explainability_v1.out

grep -q "RUNTIME_GOVERNANCE_EXPLAINABILITY_V1" /tmp/runtime_governance_explainability_v1.out
grep -q "RUNTIME_GOVERNANCE_EXPLAINABILITY_STATUS" /tmp/runtime_governance_explainability_v1.out
grep -q "RUNTIME_GOVERNANCE_EXPLAINABILITY_SUMMARY" /tmp/runtime_governance_explainability_v1.out
grep -q "основание=" /tmp/runtime_governance_explainability_v1.out
grep -q "статус_выборки=" /tmp/runtime_governance_explainability_v1.out
grep -q "RUNTIME_GOVERNANCE_EXPLAINABILITY_V1_OK" /tmp/runtime_governance_explainability_v1.out

echo "TEST_RUNTIME_GOVERNANCE_EXPLAINABILITY_V1_OK"
