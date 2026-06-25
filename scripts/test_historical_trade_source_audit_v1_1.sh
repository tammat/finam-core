#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_HISTORICAL_TRADE_SOURCE_AUDIT_V1_1 ==="

python3 -m py_compile \
  src/scripts/research/build_historical_trade_source_audit_v1_1.py

src/scripts/research/build_historical_trade_source_audit_v1_1.py \
  | tee /tmp/historical_trade_source_audit_v1_1.out

grep -q "HISTORICAL_TRADE_SOURCE_AUDIT_V1_1" /tmp/historical_trade_source_audit_v1_1.out
grep -q "SOURCE_AUDIT_EXPANDED" /tmp/historical_trade_source_audit_v1_1.out
grep -q "expanded_candidates=" /tmp/historical_trade_source_audit_v1_1.out
grep -q "VERDICT=HISTORICAL_TRADE_SOURCE_AUDIT_V1_1_READY" /tmp/historical_trade_source_audit_v1_1.out

echo "TEST_HISTORICAL_TRADE_SOURCE_AUDIT_V1_1_OK"
