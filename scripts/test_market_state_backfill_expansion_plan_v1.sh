#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_MARKET_STATE_BACKFILL_EXPANSION_PLAN_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_market_state_backfill_expansion_plan_v1.py

src/scripts/research/build_market_state_backfill_expansion_plan_v1.py \
  | tee /tmp/market_state_backfill_expansion_plan_v1.out

grep -q "current_trades=44" /tmp/market_state_backfill_expansion_plan_v1.out
grep -q "decision=SEARCH_BROADER_HISTORICAL_TRADE_SOURCES" /tmp/market_state_backfill_expansion_plan_v1.out
grep -q "next=HISTORICAL_TRADE_SOURCE_AUDIT_V1" /tmp/market_state_backfill_expansion_plan_v1.out
grep -q "VERDICT=MARKET_STATE_BACKFILL_EXPANSION_PLAN_READY" /tmp/market_state_backfill_expansion_plan_v1.out

echo "TEST_MARKET_STATE_BACKFILL_EXPANSION_PLAN_V1_OK"
