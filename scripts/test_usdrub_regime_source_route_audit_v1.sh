#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST USDRUB REGIME SOURCE ROUTE AUDIT V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/runtime/build_usdrub_regime_source_route_audit_v1.py

PYTHONPATH=src python3 src/scripts/runtime/build_usdrub_regime_source_route_audit_v1.py \
  | tee /tmp/usdrub_regime_source_route_audit_v1.log

grep -q "USDRUB_REGIME_SOURCE_ROUTE_AUDIT_V1_OK" /tmp/usdrub_regime_source_route_audit_v1.log
grep -q "USDRUB_SOURCE_ROUTE_AUDIT_SUMMARY" /tmp/usdrub_regime_source_route_audit_v1.log
grep -q "trades_today=" /tmp/usdrub_regime_source_route_audit_v1.log
grep -q "runtime_exact_match=" /tmp/usdrub_regime_source_route_audit_v1.log
grep -q "code_hits=" /tmp/usdrub_regime_source_route_audit_v1.log
grep -q "db_update=0" /tmp/usdrub_regime_source_route_audit_v1.log
grep -q "VERDICT=" /tmp/usdrub_regime_source_route_audit_v1.log

echo
echo "=== USDRUB REGIME SOURCE ROUTE AUDIT SUMMARY ==="
grep -E "USDRUB_SOURCE_RUNTIME_ROW|USDRUB_SOURCE_TRADE_ROW|USDRUB_SOURCE_CODE_HIT|runtime_exact_match=|trades_today=|code_hits=|VERDICT=" \
  /tmp/usdrub_regime_source_route_audit_v1.log | head -120

echo TEST_USDRUB_REGIME_SOURCE_ROUTE_AUDIT_V1_OK
