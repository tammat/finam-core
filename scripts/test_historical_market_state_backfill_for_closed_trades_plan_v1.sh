#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_HISTORICAL_MARKET_STATE_BACKFILL_FOR_CLOSED_TRADES_PLAN_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_historical_market_state_backfill_for_closed_trades_plan_v1.py

src/scripts/research/build_historical_market_state_backfill_for_closed_trades_plan_v1.py \
  | tee /tmp/historical_market_state_backfill_for_closed_trades_plan_v1.out

grep -q "HISTORICAL_MARKET_STATE_BACKFILL_FOR_CLOSED_TRADES_PLAN_V1" /tmp/historical_market_state_backfill_for_closed_trades_plan_v1.out
grep -q "canonical_historical_trade_source=public.closed_trades" /tmp/historical_market_state_backfill_for_closed_trades_plan_v1.out
grep -q "trade_rows=4073" /tmp/historical_market_state_backfill_for_closed_trades_plan_v1.out
grep -q "source_for_features=public.feature_snapshots" /tmp/historical_market_state_backfill_for_closed_trades_plan_v1.out
grep -q "STEP name=check_feature_snapshots_coverage" /tmp/historical_market_state_backfill_for_closed_trades_plan_v1.out
grep -q "GUARD name=no_runtime_write" /tmp/historical_market_state_backfill_for_closed_trades_plan_v1.out
grep -q "next=HISTORICAL_MARKET_STATE_BACKFILL_SOURCE_COVERAGE_V1" /tmp/historical_market_state_backfill_for_closed_trades_plan_v1.out
grep -q "VERDICT=HISTORICAL_MARKET_STATE_BACKFILL_FOR_CLOSED_TRADES_PLAN_READY" /tmp/historical_market_state_backfill_for_closed_trades_plan_v1.out

echo "TEST_HISTORICAL_MARKET_STATE_BACKFILL_FOR_CLOSED_TRADES_PLAN_V1_OK"
