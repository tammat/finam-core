#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/analytics/build_ng_short_quality_audit_v1.py

python3 src/scripts/analytics/build_ng_short_quality_audit_v1.py | \
  tee /tmp/ng_short_quality_audit_v1.log

grep -q "NG SHORT QUALITY AUDIT V1" /tmp/ng_short_quality_audit_v1.log
grep -q "SHORT_TRADES=" /tmp/ng_short_quality_audit_v1.log
grep -q "BY_STRATEGY" /tmp/ng_short_quality_audit_v1.log
grep -q "BY_ENTRY_HOUR_MSK" /tmp/ng_short_quality_audit_v1.log
grep -Eq "VERDICT=NG_SHORT_INSUFFICIENT_TRADES|VERDICT=NG_SHORT_EDGE_ACCEPTABLE|VERDICT=NG_SHORT_EDGE_WEAK_OR_NEGATIVE" \
  /tmp/ng_short_quality_audit_v1.log
grep -q "NG_SHORT_QUALITY_AUDIT_V1_OK" /tmp/ng_short_quality_audit_v1.log

echo TEST_NG_SHORT_QUALITY_AUDIT_V1_OK
