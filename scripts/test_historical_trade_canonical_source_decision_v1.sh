#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_HISTORICAL_TRADE_CANONICAL_SOURCE_DECISION_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_historical_trade_canonical_source_decision_v1.py

src/scripts/research/build_historical_trade_canonical_source_decision_v1.py \
  | tee /tmp/historical_trade_canonical_source_decision_v1.out

grep -q "HISTORICAL_TRADE_CANONICAL_SOURCE_DECISION_V1" /tmp/historical_trade_canonical_source_decision_v1.out
grep -q "best_source=public.closed_trades" /tmp/historical_trade_canonical_source_decision_v1.out
grep -q "best_rows=4073" /tmp/historical_trade_canonical_source_decision_v1.out
grep -q "canonical_historical_trade_source=public.closed_trades" /tmp/historical_trade_canonical_source_decision_v1.out
grep -q "source=public.analytics_strategy_trades_v2 rows=1962 role=cross_check" /tmp/historical_trade_canonical_source_decision_v1.out
grep -q "next=HISTORICAL_MARKET_STATE_BACKFILL_FOR_CLOSED_TRADES_PLAN_V1" /tmp/historical_trade_canonical_source_decision_v1.out
grep -q "VERDICT=HISTORICAL_TRADE_CANONICAL_SOURCE_DECISION_READY" /tmp/historical_trade_canonical_source_decision_v1.out

echo "TEST_HISTORICAL_TRADE_CANONICAL_SOURCE_DECISION_V1_OK"
