#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_MARKET_STATE_LINK_COVERAGE_REPAIR_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_market_state_link_coverage_repair_v1.py

src/scripts/research/build_market_state_link_coverage_repair_v1.py \
  | tee /tmp/market_state_link_coverage_repair_v1.out

grep -q "MARKET_STATE_LINK_COVERAGE_REPAIR_V1" /tmp/market_state_link_coverage_repair_v1.out
grep -q "trade_symbol=BRN6@RTSX" /tmp/market_state_link_coverage_repair_v1.out
grep -q "snapshot_symbol=SBER@MISX" /tmp/market_state_link_coverage_repair_v1.out
grep -q "root_cause=NO_OVERLAP_BETWEEN_TRADE_WINDOW_AND_MARKET_STATE_SNAPSHOTS" /tmp/market_state_link_coverage_repair_v1.out
grep -q "decision=BACKFILL_MARKET_STATE_FOR_TRADE_WINDOW_REQUIRED" /tmp/market_state_link_coverage_repair_v1.out
grep -q "next=MARKET_STATE_BACKFILL_FOR_TRADE_WINDOW_PLAN_V1" /tmp/market_state_link_coverage_repair_v1.out
grep -q "VERDICT=MARKET_STATE_LINK_COVERAGE_REPAIR_REQUIRES_BACKFILL" /tmp/market_state_link_coverage_repair_v1.out

echo "TEST_MARKET_STATE_LINK_COVERAGE_REPAIR_V1_OK"
