#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile \
  src/finam_core/signals/intent_semantics_v2.py \
  src/scripts/analytics/build_multi_symbol_intent_semantics_shadow_report_v1.py

python3 src/scripts/analytics/build_multi_symbol_intent_semantics_shadow_report_v1.py | \
  tee /tmp/multi_symbol_intent_semantics_shadow_report_v1.log

grep -q "MULTI SYMBOL INTENT SEMANTICS SHADOW REPORT V1" /tmp/multi_symbol_intent_semantics_shadow_report_v1.log
grep -q "ACTION_BY_SYMBOL" /tmp/multi_symbol_intent_semantics_shadow_report_v1.log
grep -q "ACTION_BY_SYMBOL_SIDE" /tmp/multi_symbol_intent_semantics_shadow_report_v1.log
grep -q "SHORT_CAPABILITY_BY_SYMBOL" /tmp/multi_symbol_intent_semantics_shadow_report_v1.log
grep -Eq "VERDICT=SHORT_SEMANTICS_FOUND_IN_MULTI_SYMBOL_FLOW|VERDICT=SHORT_SEMANTICS_ABSENT_IN_MULTI_SYMBOL_FLOW" \
  /tmp/multi_symbol_intent_semantics_shadow_report_v1.log

echo MULTI_SYMBOL_INTENT_SEMANTICS_SHADOW_REPORT_V1_OK
