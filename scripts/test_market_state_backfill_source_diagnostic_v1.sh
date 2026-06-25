#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_MARKET_STATE_BACKFILL_SOURCE_DIAGNOSTIC_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_market_state_backfill_source_diagnostic_v1.py

src/scripts/research/build_market_state_backfill_source_diagnostic_v1.py \
  | tee /tmp/market_state_backfill_source_diagnostic_v1.out

grep -q "MARKET_STATE_BACKFILL_SOURCE_DIAGNOSTIC_V1" /tmp/market_state_backfill_source_diagnostic_v1.out
grep -q "CANDIDATE_SOURCE_TABLES" /tmp/market_state_backfill_source_diagnostic_v1.out
grep -q "SOURCE_COVERAGE" /tmp/market_state_backfill_source_diagnostic_v1.out
grep -q "target_symbol=BRN6@RTSX" /tmp/market_state_backfill_source_diagnostic_v1.out
grep -q "usable_sources=" /tmp/market_state_backfill_source_diagnostic_v1.out
grep -Eq "VERDICT=MARKET_STATE_BACKFILL_SOURCE_DIAGNOSTIC_SOURCE_FOUND|VERDICT=MARKET_STATE_BACKFILL_SOURCE_DIAGNOSTIC_NO_SOURCE" /tmp/market_state_backfill_source_diagnostic_v1.out

echo "TEST_MARKET_STATE_BACKFILL_SOURCE_DIAGNOSTIC_V1_OK"
