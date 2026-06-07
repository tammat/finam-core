#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

python3 -m py_compile src/scripts/analytics/cleanup_closed_trades_duplicates_v1.py

python3 src/scripts/analytics/cleanup_closed_trades_duplicates_v1.py | tee /tmp/closed_trades_duplicate_cleanup_v1.log

grep -q "CLOSED TRADES DUPLICATE CLEANUP V1" /tmp/closed_trades_duplicate_cleanup_v1.log
grep -q "DUPLICATE_ROWS_TO_DELETE=" /tmp/closed_trades_duplicate_cleanup_v1.log
grep -q "VERDICT=DRY_RUN" /tmp/closed_trades_duplicate_cleanup_v1.log
grep -q "CLOSED_TRADES_DUPLICATE_CLEANUP_V1_OK" /tmp/closed_trades_duplicate_cleanup_v1.log

echo TEST_CLOSED_TRADES_DUPLICATE_CLEANUP_V1_OK
