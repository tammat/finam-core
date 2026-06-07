#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

python3 -m py_compile src/scripts/analytics/build_exit_reason_backfill_quality_audit_v1.py

python3 src/scripts/analytics/build_exit_reason_backfill_quality_audit_v1.py | \
  tee /tmp/exit_reason_backfill_quality_audit_v1.log

grep -q "EXIT REASON BACKFILL QUALITY AUDIT V1" /tmp/exit_reason_backfill_quality_audit_v1.log
grep -q "DUPLICATE_EXIT_TRADE_ID" /tmp/exit_reason_backfill_quality_audit_v1.log
grep -q "DUPLICATE_EXIT_FILL_ID" /tmp/exit_reason_backfill_quality_audit_v1.log
grep -q "SUSPICIOUS_REASON_AUDIT" /tmp/exit_reason_backfill_quality_audit_v1.log
grep -q "VERDICT=" /tmp/exit_reason_backfill_quality_audit_v1.log
grep -q "EXIT_REASON_BACKFILL_QUALITY_AUDIT_V1_OK" /tmp/exit_reason_backfill_quality_audit_v1.log

echo TEST_EXIT_REASON_BACKFILL_QUALITY_AUDIT_V1_OK
