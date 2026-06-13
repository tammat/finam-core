#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/analytics/build_ng_short_signal_semantics_audit_v1.py

python3 src/scripts/analytics/build_ng_short_signal_semantics_audit_v1.py | \
  tee /tmp/ng_short_signal_semantics_audit_v1.log

grep -q "NG SHORT SIGNAL SEMANTICS AUDIT V1" /tmp/ng_short_signal_semantics_audit_v1.log
grep -q "NG_SELL_TRADE_SEMANTICS" /tmp/ng_short_signal_semantics_audit_v1.log
grep -Eq "VERDICT=NG_SELL_SIGNALS_ABSENT|VERDICT=NG_SHORT_SEMANTICS_PRESENT|VERDICT=NG_SELL_ONLY_REDUCE_OR_CLOSE_LONG|VERDICT=NG_MIXED_SELL_SEMANTICS" \
  /tmp/ng_short_signal_semantics_audit_v1.log
grep -q "NG_SHORT_SIGNAL_SEMANTICS_AUDIT_V1_OK" /tmp/ng_short_signal_semantics_audit_v1.log

echo TEST_NG_SHORT_SIGNAL_SEMANTICS_AUDIT_V1_OK
