#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src
export WINDOW_HOURS=168

echo "TEST_RUNTIME_GOVERNANCE_EFFECTIVENESS_V1_START"

python -m py_compile src/scripts/analytics/build_runtime_governance_effectiveness_v1.py

python src/scripts/analytics/build_runtime_governance_effectiveness_v1.py \
  | tee /tmp/runtime_governance_effectiveness_v1_test.out

grep -q "RUNTIME_GOVERNANCE_EFFECTIVENESS_V1" /tmp/runtime_governance_effectiveness_v1_test.out
grep -q "RUNTIME_GOVERNANCE_EFFECTIVENESS_KPI" /tmp/runtime_governance_effectiveness_v1_test.out
grep -q "saved_loss_points=" /tmp/runtime_governance_effectiveness_v1_test.out
grep -q "missed_profit_points=" /tmp/runtime_governance_effectiveness_v1_test.out
grep -q "governance_alpha_points=" /tmp/runtime_governance_effectiveness_v1_test.out
grep -q "RUNTIME_GOVERNANCE_EFFECTIVENESS_SYMBOL_ALPHA" /tmp/runtime_governance_effectiveness_v1_test.out
grep -q "RUNTIME_GOVERNANCE_EFFECTIVENESS_SESSION_ALPHA" /tmp/runtime_governance_effectiveness_v1_test.out
grep -q "RUNTIME_GOVERNANCE_EFFECTIVENESS_V1_OK" /tmp/runtime_governance_effectiveness_v1_test.out

echo "TEST_RUNTIME_GOVERNANCE_EFFECTIVENESS_V1_OK"
