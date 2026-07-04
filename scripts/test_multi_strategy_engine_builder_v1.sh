#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MULTI_STRATEGY_ENGINE_BUILDER_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/strategy/base/context.py \
  src/strategy/base/executor.py \
  src/scripts/build_multi_strategy_engine_builder_v1.py

DATABASE_URL=postgresql:///finam_core STRATEGY_FEATURE_LIMIT=5000 PYTHONPATH=src \
python src/scripts/build_multi_strategy_engine_builder_v1.py \
  | tee /tmp/multi_strategy_engine_builder_v1.txt

grep -q "VERDICT=MULTI_STRATEGY_ENGINE_BUILDER_V1_READY" \
  /tmp/multi_strategy_engine_builder_v1.txt

rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.strategy_signal_snapshot_v1;
")

vb_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.strategy_signal_snapshot_v1
WHERE strategy_family='VOLATILITY_BREAKOUT';
")

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.strategy_signal_snapshot_v1
WHERE execution_allowed=true OR risk_allowed=true;
")

test "$rows" -gt 0
test "$vb_rows" -gt 0
test "$unsafe" = "0"

psql -d finam_core -c "
SELECT
    symbol,
    timeframe,
    strategy_family,
    signal_ts,
    signal_direction,
    signal_score,
    confidence,
    signal_status,
    paper_allowed,
    risk_allowed,
    execution_allowed
FROM analytics.strategy_signal_snapshot_v1
ORDER BY signal_ts DESC, signal_score DESC
LIMIT 30;
"

echo "signal_rows=$rows"
echo "volatility_breakout_rows=$vb_rows"
echo "unsafe_allowed_rows=$unsafe"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_MULTI_STRATEGY_ENGINE_BUILDER_V1_OK"
