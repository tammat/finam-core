#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile src/scripts/analytics/build_br_short_signal_generation_audit_v1.py

python3 src/scripts/analytics/build_br_short_signal_generation_audit_v1.py | \
  tee /tmp/br_short_signal_generation_audit_v1.log

grep -q "BR SHORT SIGNAL GENERATION AUDIT V1" /tmp/br_short_signal_generation_audit_v1.log
grep -q "RAW_TRADES_SIDE_BALANCE" /tmp/br_short_signal_generation_audit_v1.log
grep -q "RUNNING_POSITION_AUDIT" /tmp/br_short_signal_generation_audit_v1.log
grep -q "SELL_CONTEXT_AUDIT" /tmp/br_short_signal_generation_audit_v1.log
grep -q "VERDICT" /tmp/br_short_signal_generation_audit_v1.log
grep -Eq "VERDICT=BR_SHORT_POSITION_EXISTED|VERDICT=BR_SELL_SIGNALS_EXIST_BUT_ONLY_REDUCE_LONG|VERDICT=BR_SHORT_SIGNAL_NOT_CONFIRMED" \
  /tmp/br_short_signal_generation_audit_v1.log

echo BR_SHORT_SIGNAL_GENERATION_AUDIT_V1_OK
