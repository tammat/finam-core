#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_ENTRY_EXIT_QUALITY_ROOT_CAUSE_AUDIT_V2 ==="

python3 -m py_compile \
  src/scripts/research/build_entry_exit_quality_root_cause_audit_v2.py

src/scripts/research/build_entry_exit_quality_root_cause_audit_v2.py \
  | tee /tmp/entry_exit_quality_root_cause_audit_v2.out

grep -q "ENTRY_EXIT_QUALITY_ROOT_CAUSE_AUDIT_V2" /tmp/entry_exit_quality_root_cause_audit_v2.out
grep -q "source_table=closed_trades" /tmp/entry_exit_quality_root_cause_audit_v2.out
grep -q "section=BY_TRADE_SOURCE" /tmp/entry_exit_quality_root_cause_audit_v2.out
grep -q "section=BY_REGIME" /tmp/entry_exit_quality_root_cause_audit_v2.out
grep -q "section=BY_HOLDING_BUCKET" /tmp/entry_exit_quality_root_cause_audit_v2.out
grep -q "VERDICT=ENTRY_EXIT_QUALITY_ROOT_CAUSE_AUDIT_V2_READY" /tmp/entry_exit_quality_root_cause_audit_v2.out

echo "TEST_ENTRY_EXIT_QUALITY_ROOT_CAUSE_AUDIT_V2_OK"
