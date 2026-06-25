#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_UNIVERSE_BACKFILL_PLAN_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_universe_backfill_plan_v1.py

src/scripts/research/build_universe_backfill_plan_v1.py \
  | tee /tmp/universe_backfill_plan_v1.out

grep -q "UNIVERSE_BACKFILL_PLAN_V1" /tmp/universe_backfill_plan_v1.out
grep -q "feature_rows_usable=69181" /tmp/universe_backfill_plan_v1.out
grep -q "closed_trades_usable=437" /tmp/universe_backfill_plan_v1.out
grep -q "TARGET name=BRENT action=USE_EXISTING_FEATURES_AND_LINK_TRADES priority=1" /tmp/universe_backfill_plan_v1.out
grep -q "TARGET name=NATURAL_GAS action=USE_EXISTING_FEATURES_AND_LINK_TRADES priority=1" /tmp/universe_backfill_plan_v1.out
grep -q "TARGET name=IMOEX action=SOURCE_DISCOVERY_REQUIRED priority=3" /tmp/universe_backfill_plan_v1.out
grep -q "STEP name=run_global_context_scorecard" /tmp/universe_backfill_plan_v1.out
grep -q "GUARD name=no_micro_live_promotion" /tmp/universe_backfill_plan_v1.out
grep -q "VERDICT=UNIVERSE_BACKFILL_PLAN_READY" /tmp/universe_backfill_plan_v1.out

echo "TEST_UNIVERSE_BACKFILL_PLAN_V1_OK"
