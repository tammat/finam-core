#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_RESEARCH_MARKET_STATE_ENGINE_FRAMEWORK_PLAN_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_research_market_state_engine_framework_plan_v1.py

src/scripts/research/build_research_market_state_engine_framework_plan_v1.py \
  | tee /tmp/research_market_state_engine_framework_plan_v1.out

grep -q "RESEARCH_MARKET_STATE_ENGINE_FRAMEWORK_PLAN_V1" /tmp/research_market_state_engine_framework_plan_v1.out
grep -q "ENGINE_STAGE order=1 code=FeatureValidator" /tmp/research_market_state_engine_framework_plan_v1.out
grep -q "ENGINE_STAGE order=3 code=ClassifierPipeline" /tmp/research_market_state_engine_framework_plan_v1.out
grep -q "ENGINE_STAGE order=4 code=ConflictResolver" /tmp/research_market_state_engine_framework_plan_v1.out
grep -q "ENGINE_STAGE order=6 code=SnapshotBuilder" /tmp/research_market_state_engine_framework_plan_v1.out
grep -q "ENGINE_STAGE order=7 code=SignatureBuilder" /tmp/research_market_state_engine_framework_plan_v1.out
grep -q "ENGINE_OUTPUT name=canonical_signature" /tmp/research_market_state_engine_framework_plan_v1.out
grep -q "ENGINE_OUTPUT name=compact_signature" /tmp/research_market_state_engine_framework_plan_v1.out
grep -q "QUALITY_STATE code=CONFLICTED" /tmp/research_market_state_engine_framework_plan_v1.out
grep -q "contract=engine_never_reads_pnl" /tmp/research_market_state_engine_framework_plan_v1.out
grep -q "contract=engine_never_makes_buy_sell_hold_decision" /tmp/research_market_state_engine_framework_plan_v1.out
grep -q "contract=engine_is_deterministic" /tmp/research_market_state_engine_framework_plan_v1.out
grep -q "contract=engine_is_stateless" /tmp/research_market_state_engine_framework_plan_v1.out
grep -q "rule=edge_discovery_starts_after_engine" /tmp/research_market_state_engine_framework_plan_v1.out
grep -q "rule=no_runtime_execution_changes" /tmp/research_market_state_engine_framework_plan_v1.out
grep -q "VERDICT=RESEARCH_MARKET_STATE_ENGINE_FRAMEWORK_PLAN_READY" /tmp/research_market_state_engine_framework_plan_v1.out

echo "TEST_RESEARCH_MARKET_STATE_ENGINE_FRAMEWORK_PLAN_V1_OK"
