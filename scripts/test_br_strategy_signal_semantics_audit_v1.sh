#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile \
  src/finam_core/signals/intent_semantics_v2.py \
  src/scripts/analytics/build_br_strategy_signal_semantics_audit_v1.py

python3 src/scripts/analytics/build_br_strategy_signal_semantics_audit_v1.py | \
  tee /tmp/br_strategy_signal_semantics_audit_v1.log

grep -q "BR STRATEGY SIGNAL SEMANTICS AUDIT V1" /tmp/br_strategy_signal_semantics_audit_v1.log
grep -q "TRADE_ACTION_SUMMARY" /tmp/br_strategy_signal_semantics_audit_v1.log
grep -q "BR_SELL_TRADE_SEMANTICS" /tmp/br_strategy_signal_semantics_audit_v1.log
grep -q "SIGNAL_LAYER_SUMMARY" /tmp/br_strategy_signal_semantics_audit_v1.log
grep -Eq "VERDICT=BR_SELL_SIGNALS_EXIST_BUT_ONLY_REDUCE_OR_CLOSE_LONG|VERDICT=BR_SHORT_SEMANTICS_ALREADY_EXISTS|VERDICT=BR_SELL_SIGNAL_ABSENT_OR_UNCLEAR" \
  /tmp/br_strategy_signal_semantics_audit_v1.log

echo BR_STRATEGY_SIGNAL_SEMANTICS_AUDIT_V1_OK
