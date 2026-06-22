#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EQUITIES_CLEAN_TRADE_SOURCE_AUDIT_V1 ==="

python3 -m py_compile src/scripts/research/build_equities_clean_trade_source_audit_v1.py

python3 src/scripts/research/build_equities_clean_trade_source_audit_v1.py \
  | tee /tmp/equities_clean_trade_source_audit_v1.log

grep -q "EQUITY_TRADE_SOURCE_SUMMARY" /tmp/equities_clean_trade_source_audit_v1.log
grep -q "DECISION=" /tmp/equities_clean_trade_source_audit_v1.log
grep -q "VERDICT=EQUITIES_CLEAN_TRADE_SOURCE_AUDIT_READY" /tmp/equities_clean_trade_source_audit_v1.log

echo "VERDICT=EQUITIES_CLEAN_TRADE_SOURCE_AUDIT_TEST_OK"
echo "TEST_EQUITIES_CLEAN_TRADE_SOURCE_AUDIT_V1_OK"
