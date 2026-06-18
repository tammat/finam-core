#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST MARKET SIGNAL CATALOG V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile \
  src/scripts/research/build_market_signal_catalog_v1.py

MARKET_SIGNAL_CATALOG_LOOKBACK="${MARKET_SIGNAL_CATALOG_LOOKBACK:-30 days}" \
MARKET_SIGNAL_CATALOG_LIMIT="${MARKET_SIGNAL_CATALOG_LIMIT:-50000}" \
PYTHONPATH=src python3 src/scripts/research/build_market_signal_catalog_v1.py \
  | tee /tmp/market_signal_catalog_v1.log

grep -q "MARKET_SIGNAL_CATALOG_V1_OK" /tmp/market_signal_catalog_v1.log
grep -q "MARKET_SIGNAL_CATALOG_ROWS" /tmp/market_signal_catalog_v1.log
grep -q "MARKET_SIGNAL_CATALOG_SUMMARY" /tmp/market_signal_catalog_v1.log
grep -q "VERDICT=" /tmp/market_signal_catalog_v1.log

echo
echo "=== MARKET SIGNAL CATALOG SUMMARY ==="
grep -E "MARKET_SIGNAL_CATALOG_ROW|rows_total=|trades_total=|unknown_or_unclassified_rows=|VERDICT=" \
  /tmp/market_signal_catalog_v1.log \
  | head -120

echo TEST_MARKET_SIGNAL_CATALOG_V1_OK
