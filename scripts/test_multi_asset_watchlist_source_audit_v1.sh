#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST MULTI ASSET WATCHLIST SOURCE AUDIT V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"
echo "orders_create=0"
echo "execution_intents_create=0"

python3 -m py_compile src/scripts/research/build_multi_asset_watchlist_source_audit_v1.py

PYTHONPATH=src \
RUNTIME_ALLOW_TRADING=0 EXECUTION_ENABLED=0 REAL_TRADING_ENABLED=0 \
python3 src/scripts/research/build_multi_asset_watchlist_source_audit_v1.py \
  | tee /tmp/multi_asset_watchlist_source_audit_v1.log

grep -q "MULTI_ASSET_WATCHLIST_SOURCE_AUDIT_V1_OK" /tmp/multi_asset_watchlist_source_audit_v1.log
grep -q "WATCHLIST_SOURCE_CANDIDATES" /tmp/multi_asset_watchlist_source_audit_v1.log
grep -q "top_path=" /tmp/multi_asset_watchlist_source_audit_v1.log
grep -q "VERDICT=" /tmp/multi_asset_watchlist_source_audit_v1.log
grep -q "orders_create=0" /tmp/multi_asset_watchlist_source_audit_v1.log
grep -q "execution_intents_create=0" /tmp/multi_asset_watchlist_source_audit_v1.log

echo "=== WATCHLIST SOURCE SUMMARY ==="
grep -E "WATCHLIST_SOURCE_ROW|top_path=|top_score=|VERDICT=" \
  /tmp/multi_asset_watchlist_source_audit_v1.log | head -40

echo TEST_MULTI_ASSET_WATCHLIST_SOURCE_AUDIT_V1_OK
