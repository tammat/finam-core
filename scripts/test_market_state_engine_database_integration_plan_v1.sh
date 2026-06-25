#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_MARKET_STATE_ENGINE_DATABASE_INTEGRATION_PLAN_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_market_state_engine_database_integration_plan_v1.py

src/scripts/research/build_market_state_engine_database_integration_plan_v1.py \
  | tee /tmp/market_state_engine_database_integration_plan_v1.out

grep -q "MARKET_STATE_ENGINE_DATABASE_INTEGRATION_PLAN_V1" /tmp/market_state_engine_database_integration_plan_v1.out
grep -q "TABLE name=research.market_state_snapshots_v1" /tmp/market_state_engine_database_integration_plan_v1.out
grep -q "TABLE name=research.market_state_snapshot_values_v1" /tmp/market_state_engine_database_integration_plan_v1.out
grep -q "FLOW_STEP name=SnapshotWriter" /tmp/market_state_engine_database_integration_plan_v1.out
grep -q "GUARD name=postgres_only" /tmp/market_state_engine_database_integration_plan_v1.out
grep -q "GUARD name=no_sqlite" /tmp/market_state_engine_database_integration_plan_v1.out
grep -q "GUARD name=transaction_required" /tmp/market_state_engine_database_integration_plan_v1.out
grep -q "rule=market_state_snapshot_is_immutable" /tmp/market_state_engine_database_integration_plan_v1.out
grep -q "rule=no_runtime_execution_changes" /tmp/market_state_engine_database_integration_plan_v1.out
grep -q "VERDICT=MARKET_STATE_ENGINE_DATABASE_INTEGRATION_PLAN_READY" /tmp/market_state_engine_database_integration_plan_v1.out

echo "TEST_MARKET_STATE_ENGINE_DATABASE_INTEGRATION_PLAN_V1_OK"
