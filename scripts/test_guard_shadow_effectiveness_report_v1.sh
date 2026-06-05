#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile src/scripts/analytics/build_guard_shadow_effectiveness_report_v1.py

python3 src/scripts/analytics/build_guard_shadow_effectiveness_report_v1.py \
  --since "24 hours ago" | tee /tmp/guard_shadow_effectiveness_report_v1.log

grep -q "GUARD SHADOW EFFECTIVENESS REPORT V1" /tmp/guard_shadow_effectiveness_report_v1.log
grep -q "SHADOW_TOTAL" /tmp/guard_shadow_effectiveness_report_v1.log
grep -Eq "VERDICT=OK|VERDICT=NO_SHADOW_EVENTS_YET" /tmp/guard_shadow_effectiveness_report_v1.log

echo GUARD_SHADOW_EFFECTIVENESS_REPORT_V1_OK
