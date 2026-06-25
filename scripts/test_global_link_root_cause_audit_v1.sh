#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_GLOBAL_LINK_ROOT_CAUSE_AUDIT_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_global_link_root_cause_audit_v1.py

src/scripts/research/build_global_link_root_cause_audit_v1.py \
  | tee /tmp/global_link_root_cause_audit_v1.out

grep -q "GLOBAL_LINK_ROOT_CAUSE_AUDIT_V1" /tmp/global_link_root_cause_audit_v1.out
grep -q "EXECUTIVE_SUMMARY" /tmp/global_link_root_cause_audit_v1.out
grep -q "closed_trades=" /tmp/global_link_root_cause_audit_v1.out
grep -q "linked=" /tmp/global_link_root_cause_audit_v1.out
grep -q "lost=" /tmp/global_link_root_cause_audit_v1.out
grep -q "coverage=" /tmp/global_link_root_cause_audit_v1.out
grep -q "ROOT_CAUSE_SUMMARY" /tmp/global_link_root_cause_audit_v1.out
grep -q "INSTRUMENT_SUMMARY" /tmp/global_link_root_cause_audit_v1.out
grep -Eq "VERDICT=GLOBAL_LINK_ROOT_CAUSE_AUDIT_READY_FOR_CONTEXT_LINKING|VERDICT=GLOBAL_LINK_ROOT_CAUSE_AUDIT_WARNING_REPAIR_RECOMMENDED|VERDICT=GLOBAL_LINK_ROOT_CAUSE_AUDIT_REPAIR_REQUIRED" /tmp/global_link_root_cause_audit_v1.out

echo "TEST_GLOBAL_LINK_ROOT_CAUSE_AUDIT_V1_OK"
