#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_BR_GOVERNANCE_CONFLICT_AUDIT_V1_START"

python -m py_compile src/scripts/analytics/build_br_governance_conflict_audit_v1.py

python src/scripts/analytics/build_br_governance_conflict_audit_v1.py \
  --hour 12 \
  --side BUY \
  --window-days 30 \
  --recent-days 7 | tee /tmp/br_governance_conflict_audit_v1.out

grep -q "BR_GOVERNANCE_CONFLICT_AUDIT_V1" /tmp/br_governance_conflict_audit_v1.out
grep -q "BR_CONFLICT_FINANCIAL" /tmp/br_governance_conflict_audit_v1.out
grep -q "BR_CONFLICT_GOVERNANCE" /tmp/br_governance_conflict_audit_v1.out
grep -q "BR_CONFLICT_REASON" /tmp/br_governance_conflict_audit_v1.out
grep -q "BR_CONFLICT_ROOT_CAUSE" /tmp/br_governance_conflict_audit_v1.out
grep -q "BR_GOVERNANCE_CONFLICT_AUDIT_V1_OK" /tmp/br_governance_conflict_audit_v1.out

echo "TEST_BR_GOVERNANCE_CONFLICT_AUDIT_V1_OK"
