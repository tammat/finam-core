#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_MARKET_STATE_LINK_COVERAGE_DIAGNOSTIC_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_market_state_link_coverage_diagnostic_v1.py

src/scripts/research/build_market_state_link_coverage_diagnostic_v1.py \
  | tee /tmp/market_state_link_coverage_diagnostic_v1.out

grep -q "MARKET_STATE_LINK_COVERAGE_DIAGNOSTIC_V1" /tmp/market_state_link_coverage_diagnostic_v1.out
grep -q "TRADE_OUTCOMES_RANGE" /tmp/market_state_link_coverage_diagnostic_v1.out
grep -q "MARKET_STATE_SNAPSHOT_RANGE" /tmp/market_state_link_coverage_diagnostic_v1.out
grep -q "LINK_QUALITY_CURRENT" /tmp/market_state_link_coverage_diagnostic_v1.out
grep -q "TRADE_TO_SNAPSHOT_COVERAGE" /tmp/market_state_link_coverage_diagnostic_v1.out
grep -q "SNAPSHOT_RANGES" /tmp/market_state_link_coverage_diagnostic_v1.out
grep -q "VERDICT=MARKET_STATE_LINK_COVERAGE_DIAGNOSTIC_READY" /tmp/market_state_link_coverage_diagnostic_v1.out

echo "TEST_MARKET_STATE_LINK_COVERAGE_DIAGNOSTIC_V1_OK"
