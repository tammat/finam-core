#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_MARKET_STATE_COMMISSION_SOURCE_AUDIT_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_market_state_commission_source_audit_v1.py

src/scripts/research/build_market_state_commission_source_audit_v1.py \
  | tee /tmp/market_state_commission_source_audit_v1.out

grep -q "MARKET_STATE_COMMISSION_SOURCE_AUDIT_V1" /tmp/market_state_commission_source_audit_v1.out
grep -q "TRADE_OUTCOMES_COLUMNS" /tmp/market_state_commission_source_audit_v1.out
grep -q "COMMISSION_SUMMARY" /tmp/market_state_commission_source_audit_v1.out
grep -q "LINKED_PNL_COMMISSION" /tmp/market_state_commission_source_audit_v1.out
grep -q "commission_nonzero=" /tmp/market_state_commission_source_audit_v1.out
grep -Eq "VERDICT=MARKET_STATE_COMMISSION_SOURCE_AUDIT_OK|VERDICT=MARKET_STATE_COMMISSION_SOURCE_AUDIT_COMMISSION_ZERO_SOURCE_WEAK" /tmp/market_state_commission_source_audit_v1.out

echo "TEST_MARKET_STATE_COMMISSION_SOURCE_AUDIT_V1_OK"
