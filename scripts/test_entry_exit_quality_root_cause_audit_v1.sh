#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_ENTRY_EXIT_QUALITY_ROOT_CAUSE_AUDIT_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_entry_exit_quality_root_cause_audit_v1.py

src/scripts/research/build_entry_exit_quality_root_cause_audit_v1.py \
  | tee /tmp/entry_exit_quality_root_cause_audit_v1.out

grep -q "ENTRY_EXIT_QUALITY_ROOT_CAUSE_AUDIT_V1" /tmp/entry_exit_quality_root_cause_audit_v1.out
grep -q "SCHEMA_DETECTION" /tmp/entry_exit_quality_root_cause_audit_v1.out
grep -q "EXIT_REASON_ROWS" /tmp/entry_exit_quality_root_cause_audit_v1.out
grep -Eq "VERDICT=ENTRY_EXIT_QUALITY_ROOT_CAUSE_AUDIT_(READY|SCHEMA_ONLY)" /tmp/entry_exit_quality_root_cause_audit_v1.out

echo "TEST_ENTRY_EXIT_QUALITY_ROOT_CAUSE_AUDIT_V1_OK"
