#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile \
  src/finam_core/signals/intent_semantics_v2.py \
  src/scripts/analytics/build_br_intent_semantics_v2_shadow_report.py

python3 src/scripts/analytics/build_br_intent_semantics_v2_shadow_report.py | \
  tee /tmp/br_intent_semantics_v2_shadow_report.log

grep -q "BR INTENT SEMANTICS V2 SHADOW REPORT" /tmp/br_intent_semantics_v2_shadow_report.log
grep -q "ACTION_SUMMARY" /tmp/br_intent_semantics_v2_shadow_report.log
grep -q "ACTION_BY_SIDE" /tmp/br_intent_semantics_v2_shadow_report.log
grep -q "SHORT_SEMANTICS_SUMMARY" /tmp/br_intent_semantics_v2_shadow_report.log
grep -Eq "VERDICT=BR_SHORT_SEMANTICS_PRESENT|VERDICT=BR_SHORT_SEMANTICS_ABSENT" \
  /tmp/br_intent_semantics_v2_shadow_report.log

echo BR_INTENT_SEMANTICS_V2_SHADOW_REPORT_OK
