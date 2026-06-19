#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST DIRTY TRADE ORIGIN AUDIT V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/research/build_dirty_trade_origin_audit_v1.py

PYTHONPATH=src python3 src/scripts/research/build_dirty_trade_origin_audit_v1.py \
  | tee /tmp/dirty_trade_origin_audit_v1.log

grep -q "DIRTY_TRADE_ORIGIN_AUDIT_V1_OK" /tmp/dirty_trade_origin_audit_v1.log
grep -q "DIRTY_TRADE_ORIGIN_AUDIT_SUMMARY" /tmp/dirty_trade_origin_audit_v1.log
grep -q "dirty_rows=" /tmp/dirty_trade_origin_audit_v1.log
grep -q "unknown_source_rows=" /tmp/dirty_trade_origin_audit_v1.log
grep -q "zero_commission_rows=" /tmp/dirty_trade_origin_audit_v1.log
grep -q "VERDICT=" /tmp/dirty_trade_origin_audit_v1.log
grep -q "db_update=0" /tmp/dirty_trade_origin_audit_v1.log

echo
echo "=== DIRTY TRADE ORIGIN AUDIT SUMMARY ==="
grep -E "DIRTY_TRADE_ORIGIN_REASON_ROW|DIRTY_TRADE_ORIGIN_GROUP_ROW|DIRTY_TRADE_ORIGIN_STRATEGY_SYMBOL_ROW|rows_total=|dirty_rows=|unknown_source_rows=|unknown_reason_rows=|zero_commission_rows=|missing_strategy_rows=|missing_timeframe_rows=|VERDICT=" \
  /tmp/dirty_trade_origin_audit_v1.log | head -120

echo TEST_DIRTY_TRADE_ORIGIN_AUDIT_V1_OK
