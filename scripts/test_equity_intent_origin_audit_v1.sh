#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST EQUITY INTENT ORIGIN AUDIT V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/research/build_equity_intent_origin_audit_v1.py

PYTHONPATH=src python3 src/scripts/research/build_equity_intent_origin_audit_v1.py \
  | tee /tmp/equity_intent_origin_audit_v1.log

grep -q "EQUITY_INTENT_ORIGIN_AUDIT_V1_OK" /tmp/equity_intent_origin_audit_v1.log
grep -q "EQUITY_INTENT_ORIGIN_AUDIT_SUMMARY" /tmp/equity_intent_origin_audit_v1.log
grep -q "execution_intents_total=" /tmp/equity_intent_origin_audit_v1.log
grep -q "orphan_legacy_intents=" /tmp/equity_intent_origin_audit_v1.log
grep -q "VERDICT=" /tmp/equity_intent_origin_audit_v1.log
grep -q "db_update=0" /tmp/equity_intent_origin_audit_v1.log

echo
echo "=== EQUITY INTENT ORIGIN SUMMARY ==="
grep -E "EQUITY_INTENT_SCHEMA_COLUMN_ROW|EQUITY_INTENT_ORIGIN_GROUP_ROW|signals_total=|execution_intents_total=|orphan_legacy_intents=|review_required_intents=|VERDICT=" \
  /tmp/equity_intent_origin_audit_v1.log | head -120

echo TEST_EQUITY_INTENT_ORIGIN_AUDIT_V1_OK
