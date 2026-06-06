#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile \
  src/finam_core/signals/intent_semantics_v2.py \
  src/scripts/analytics/build_multi_symbol_short_sanity_audit_v1.py

python3 src/scripts/analytics/build_multi_symbol_short_sanity_audit_v1.py | \
  tee /tmp/multi_symbol_short_sanity_audit_v1.log

grep -q "MULTI SYMBOL SHORT SANITY AUDIT V1" /tmp/multi_symbol_short_sanity_audit_v1.log
grep -q "SHORT_BY_SYMBOL" /tmp/multi_symbol_short_sanity_audit_v1.log
grep -q "SHORT_BY_STRATEGY_ACTION" /tmp/multi_symbol_short_sanity_audit_v1.log
grep -q "SANITY_FLAGS" /tmp/multi_symbol_short_sanity_audit_v1.log
grep -Eq "VERDICT=SHORT_ENGINE_EXISTS_BUT_BR_SHORT_ABSENT|VERDICT=BR_SHORT_FLOW_FOUND|VERDICT=SHORT_FLOW_DIRTY_UNKNOWN_DOMINATED|VERDICT=SHORT_FLOW_REQUIRES_MANUAL_REVIEW" \
  /tmp/multi_symbol_short_sanity_audit_v1.log

echo MULTI_SYMBOL_SHORT_SANITY_AUDIT_V1_OK
