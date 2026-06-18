#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST RUNTIME ACTIVE UNIVERSE SCHEMA AUDIT V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile \
  src/scripts/research/build_runtime_active_universe_schema_audit_v1.py

PYTHONPATH=src python3 src/scripts/research/build_runtime_active_universe_schema_audit_v1.py \
  | tee /tmp/runtime_active_universe_schema_audit_v1.log

grep -q "RUNTIME_ACTIVE_UNIVERSE_SCHEMA_AUDIT_V1_OK" /tmp/runtime_active_universe_schema_audit_v1.log
grep -q "VERDICT=RUNTIME_ACTIVE_UNIVERSE_SCHEMA_AUDIT_READY" /tmp/runtime_active_universe_schema_audit_v1.log
grep -q "RUNTIME_ACTIVE_UNIVERSE_COLUMNS" /tmp/runtime_active_universe_schema_audit_v1.log
grep -q "RUNTIME_ACTIVE_UNIVERSE_ROWS" /tmp/runtime_active_universe_schema_audit_v1.log
grep -q "TRADE_DATES_RECENT" /tmp/runtime_active_universe_schema_audit_v1.log

echo TEST_RUNTIME_ACTIVE_UNIVERSE_SCHEMA_AUDIT_V1_OK
