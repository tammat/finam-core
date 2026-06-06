#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile src/scripts/analytics/build_br_signal_intent_semantics_audit_v1.py

python3 src/scripts/analytics/build_br_signal_intent_semantics_audit_v1.py | \
  tee /tmp/br_signal_intent_semantics_audit_v1.log

grep -q "BR SIGNAL INTENT SEMANTICS AUDIT V1" /tmp/br_signal_intent_semantics_audit_v1.log
grep -q "SIGNALS_AUDIT" /tmp/br_signal_intent_semantics_audit_v1.log
grep -q "EXECUTION_INTENTS_AUDIT" /tmp/br_signal_intent_semantics_audit_v1.log
grep -q "POSITION_SEMANTICS_INFERENCE" /tmp/br_signal_intent_semantics_audit_v1.log
grep -Eq "VERDICT=EXPLICIT_INTENT_SEMANTICS_FOUND|VERDICT=SEMANTICS_INFERRED_FROM_POSITION_ONLY|VERDICT=NO_EXPLICIT_OPEN_CLOSE_SEMANTICS" \
  /tmp/br_signal_intent_semantics_audit_v1.log

echo BR_SIGNAL_INTENT_SEMANTICS_AUDIT_V1_OK
