#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST STORAGE TRADE WRITER CONTEXT AUDIT V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile \
  src/scripts/research/build_storage_trade_writer_context_audit_v1.py

PYTHONPATH=src python3 src/scripts/research/build_storage_trade_writer_context_audit_v1.py \
  | tee /tmp/storage_trade_writer_context_audit_v1.log

grep -q "STORAGE_TRADE_WRITER_CONTEXT_AUDIT_V1_OK" /tmp/storage_trade_writer_context_audit_v1.log
grep -q "VERDICT=STORAGE_TRADE_WRITER_CONTEXT_AUDIT_READY" /tmp/storage_trade_writer_context_audit_v1.log
grep -q "STORAGE_TRADE_WRITER_CONTEXT_AUDIT_SUMMARY" /tmp/storage_trade_writer_context_audit_v1.log
grep -q "STORAGE_WRITER_FILE path=src/finam_core/storage/postgres.py" /tmp/storage_trade_writer_context_audit_v1.log
grep -q "STORAGE_WRITER_FILE path=src/finam_core/storage/postgres_logger.py" /tmp/storage_trade_writer_context_audit_v1.log
grep -q "STORAGE_WRITER_FILE path=src/finam_core/execution/fill_persistence_service.py" /tmp/storage_trade_writer_context_audit_v1.log

echo
echo "=== STORAGE WRITER SUMMARY ==="
grep -E "STORAGE_WRITER_FILE_SUMMARY|STORAGE_TRADE_WRITER_CONTEXT_AUDIT_SUMMARY|VERDICT=" \
  /tmp/storage_trade_writer_context_audit_v1.log

echo TEST_STORAGE_TRADE_WRITER_CONTEXT_AUDIT_V1_OK
