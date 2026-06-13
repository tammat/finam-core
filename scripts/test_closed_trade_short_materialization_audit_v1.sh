#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile src/scripts/analytics/build_closed_trade_short_materialization_audit_v1.py

python3 src/scripts/analytics/build_closed_trade_short_materialization_audit_v1.py | \
  tee /tmp/closed_trade_short_materialization_audit_v1.log

grep -q "CLOSED TRADE SHORT MATERIALIZATION AUDIT V1" /tmp/closed_trade_short_materialization_audit_v1.log
grep -q "RAW_TRADES_BR" /tmp/closed_trade_short_materialization_audit_v1.log
grep -q "RAW_FILLS_BR" /tmp/closed_trade_short_materialization_audit_v1.log
grep -q "CLOSED_TRADES_BR" /tmp/closed_trade_short_materialization_audit_v1.log
grep -q "CHAIN_TO_CLOSED_AUDIT" /tmp/closed_trade_short_materialization_audit_v1.log
grep -q "NULL_ROOT_SHORT_AUDIT" /tmp/closed_trade_short_materialization_audit_v1.log
grep -Eq "VERDICT=SHORT_MATERIALIZATION_OK|VERDICT=SHORT_LOST_IN_CLOSED_TRADES|VERDICT=ROOT_SYMBOL_MAPPING_BROKEN|VERDICT=SHORT_MATERIALIZATION_AND_ROOT_MAPPING_BROKEN" \
  /tmp/closed_trade_short_materialization_audit_v1.log

echo CLOSED_TRADE_SHORT_MATERIALIZATION_AUDIT_V1_OK
