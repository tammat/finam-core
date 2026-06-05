#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile src/scripts/analytics/build_guard_shadow_accumulation_report_v1.py

python3 src/scripts/analytics/build_guard_shadow_accumulation_report_v1.py \
  --since "24 hours" | tee /tmp/guard_shadow_accumulation_report_v1.log

grep -q "GUARD SHADOW ACCUMULATION REPORT V1" /tmp/guard_shadow_accumulation_report_v1.log
grep -q "TOTAL_EVENTS=" /tmp/guard_shadow_accumulation_report_v1.log
grep -Eq "VERDICT=OK|VERDICT=NO_TABLE_YET|VERDICT=NO_SHADOW_ACCUMULATION_EVENTS_YET" /tmp/guard_shadow_accumulation_report_v1.log

echo GUARD_SHADOW_ACCUMULATION_REPORT_V1_OK
