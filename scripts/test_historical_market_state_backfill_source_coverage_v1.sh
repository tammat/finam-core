#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_HISTORICAL_MARKET_STATE_BACKFILL_SOURCE_COVERAGE_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_historical_market_state_backfill_source_coverage_v1.py

src/scripts/research/build_historical_market_state_backfill_source_coverage_v1.py \
  | tee /tmp/historical_market_state_backfill_source_coverage_v1.out

grep -q "HISTORICAL_MARKET_STATE_BACKFILL_SOURCE_COVERAGE_V1" /tmp/historical_market_state_backfill_source_coverage_v1.out
grep -q "SOURCE_COVERAGE_ROWS" /tmp/historical_market_state_backfill_source_coverage_v1.out
grep -q "windows_total=" /tmp/historical_market_state_backfill_source_coverage_v1.out
grep -q "full_coverage_windows=" /tmp/historical_market_state_backfill_source_coverage_v1.out
grep -q "closed_trades_total=" /tmp/historical_market_state_backfill_source_coverage_v1.out
grep -Eq "VERDICT=HISTORICAL_MARKET_STATE_BACKFILL_SOURCE_COVERAGE_READY|VERDICT=HISTORICAL_MARKET_STATE_BACKFILL_SOURCE_COVERAGE_NO_FULL_WINDOWS" /tmp/historical_market_state_backfill_source_coverage_v1.out

echo "TEST_HISTORICAL_MARKET_STATE_BACKFILL_SOURCE_COVERAGE_V1_OK"
