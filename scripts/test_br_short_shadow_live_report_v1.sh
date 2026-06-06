#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/analytics/build_br_short_shadow_live_report_v1.py

python3 src/scripts/analytics/build_br_short_shadow_live_report_v1.py | \
  tee /tmp/br_short_shadow_live_report_v1.log

grep -q "BR SHORT SHADOW LIVE REPORT V1" /tmp/br_short_shadow_live_report_v1.log
grep -q "TABLE_EXISTS=" /tmp/br_short_shadow_live_report_v1.log
grep -Eq "VERDICT=NO_TABLE|VERDICT=WAIT_FOR_LIVE_SHADOW_ROWS|VERDICT=ACCUMULATE_MORE_SHADOW_DATA|VERDICT=ENOUGH_SHADOW_DATA_FOR_PAPER_CANDIDATE_REVIEW" \
  /tmp/br_short_shadow_live_report_v1.log

echo BR_SHORT_SHADOW_LIVE_REPORT_V1_OK
