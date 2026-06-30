#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_GOLD_RECENT_DEGRADATION_ROOT_CAUSE_AUDIT_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_gold_recent_degradation_root_cause_audit_v1.py

src/scripts/research/build_gold_recent_degradation_root_cause_audit_v1.py \
  | tee /tmp/gold_recent_degradation_root_cause_audit_v1.out

grep -q "ROOT_CAUSE_ROW section=PERIOD symbol=GDU6@RTSX" /tmp/gold_recent_degradation_root_cause_audit_v1.out
grep -q "ROOT_CAUSE_ROW section=PERIOD symbol=GLU6@RTSX" /tmp/gold_recent_degradation_root_cause_audit_v1.out
grep -q "section=DAY" /tmp/gold_recent_degradation_root_cause_audit_v1.out
grep -q "section=HOUR" /tmp/gold_recent_degradation_root_cause_audit_v1.out
grep -q "VERDICT=GOLD_RECENT_DEGRADATION_ROOT_CAUSE_AUDIT_READY" /tmp/gold_recent_degradation_root_cause_audit_v1.out

echo "TEST_GOLD_RECENT_DEGRADATION_ROOT_CAUSE_AUDIT_V1_OK"
