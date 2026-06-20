#!/usr/bin/env bash
set -euo pipefail

echo "=== EQUITY_BREAKOUT_WATCHER_MARKET_BARS_SOURCE_AUDIT_V1 ==="

out="$(mktemp)"

python3 -m py_compile \
  src/scripts/research/build_equity_breakout_watcher_market_bars_source_audit_v1.py

python3 src/scripts/research/build_equity_breakout_watcher_market_bars_source_audit_v1.py | tee "$out"

grep -q "VERDICT=EQUITY_BREAKOUT_WATCHER_MARKET_BARS_SOURCE_AUDIT_READY" "$out"
grep -q "TEST_EQUITY_BREAKOUT_WATCHER_MARKET_BARS_SOURCE_AUDIT_V1_OK" "$out"
grep -q '"db_update": 0' "$out"
grep -q '"runtime_changed": 0' "$out"
grep -q '"execution_changed": 0' "$out"

echo "VERDICT=EQUITY_BREAKOUT_WATCHER_MARKET_BARS_SOURCE_AUDIT_TEST_OK"
echo "TEST_EQUITY_BREAKOUT_WATCHER_MARKET_BARS_SOURCE_AUDIT_V1_OK"
