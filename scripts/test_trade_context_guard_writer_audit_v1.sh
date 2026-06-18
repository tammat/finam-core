#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST TRADE CONTEXT GUARD WRITER AUDIT V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/research/build_trade_context_guard_writer_audit_v1.py

PYTHONPATH=src python3 src/scripts/research/build_trade_context_guard_writer_audit_v1.py \
  | tee /tmp/trade_context_guard_writer_audit_v1.log

grep -q "TRADE_CONTEXT_GUARD_WRITER_AUDIT_V1_OK" /tmp/trade_context_guard_writer_audit_v1.log
grep -q "TRADE_CONTEXT_GUARD_WRITER_AUDIT_SUMMARY" /tmp/trade_context_guard_writer_audit_v1.log
grep -q "insert_hits=" /tmp/trade_context_guard_writer_audit_v1.log
grep -q "log_trade_hits=" /tmp/trade_context_guard_writer_audit_v1.log
grep -q "log_fill_hits=" /tmp/trade_context_guard_writer_audit_v1.log
grep -q "db_update=0" /tmp/trade_context_guard_writer_audit_v1.log
grep -q "VERDICT=" /tmp/trade_context_guard_writer_audit_v1.log

echo
echo "=== TRADE CONTEXT GUARD WRITER AUDIT SUMMARY ==="
grep -E "AUDIT_HIT file=src/finam_core/storage/postgres|AUDIT_HIT file=src/finam_core/storage/postgres_logger|total_hits=|insert_hits=|log_trade_hits=|log_fill_hits=|guard_hits=|VERDICT=" \
  /tmp/trade_context_guard_writer_audit_v1.log

echo TEST_TRADE_CONTEXT_GUARD_WRITER_AUDIT_V1_OK
