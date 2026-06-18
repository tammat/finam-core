#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST TRADE CONTEXT GUARD ALT WRITER ROOT CAUSE V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/runtime/build_trade_context_guard_alt_writer_root_cause_v1.py

PYTHONPATH=src python3 src/scripts/runtime/build_trade_context_guard_alt_writer_root_cause_v1.py \
  | tee /tmp/trade_context_guard_alt_writer_root_cause_v1.log

grep -q "TRADE_CONTEXT_GUARD_ALT_WRITER_ROOT_CAUSE_V1_OK" /tmp/trade_context_guard_alt_writer_root_cause_v1.log
grep -q "ALT_WRITER_ROOT_CAUSE_SUMMARY" /tmp/trade_context_guard_alt_writer_root_cause_v1.log
grep -q "unknown_rows=" /tmp/trade_context_guard_alt_writer_root_cause_v1.log
grep -q "db_update=0" /tmp/trade_context_guard_alt_writer_root_cause_v1.log
grep -q "VERDICT=" /tmp/trade_context_guard_alt_writer_root_cause_v1.log

echo
echo "=== ALT WRITER ROOT CAUSE SUMMARY ==="
grep -E "ALT_WRITER_UNKNOWN_ROW|ALT_WRITER_NEARBY_ROW|ALT_WRITER_CODE_HIT|unknown_rows=|suspected_alt_writer=|VERDICT=" \
  /tmp/trade_context_guard_alt_writer_root_cause_v1.log

echo TEST_TRADE_CONTEXT_GUARD_ALT_WRITER_ROOT_CAUSE_V1_OK
