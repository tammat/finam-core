#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_RESEARCH_STRATEGY_RECOMMENDATION_ENGINE_PLAN_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_research_strategy_recommendation_engine_plan_v1.py

src/scripts/research/build_research_strategy_recommendation_engine_plan_v1.py \
  | tee /tmp/research_strategy_recommendation_engine_plan_v1.out

grep -q "RESEARCH_STRATEGY_RECOMMENDATION_ENGINE_PLAN_V1" /tmp/research_strategy_recommendation_engine_plan_v1.out
grep -q "RECOMMENDATION_STAGE order=1 code=CandidateStateSelector" /tmp/research_strategy_recommendation_engine_plan_v1.out
grep -q "RECOMMENDATION_STAGE order=3 code=StrategyStateMatcher" /tmp/research_strategy_recommendation_engine_plan_v1.out
grep -q "RECOMMENDATION_STAGE order=4 code=RiskFitEvaluator" /tmp/research_strategy_recommendation_engine_plan_v1.out
grep -q "RECOMMENDATION_STAGE order=5 code=ExecutionFitEvaluator" /tmp/research_strategy_recommendation_engine_plan_v1.out
grep -q "RECOMMENDATION_STAGE order=7 code=PromotionGate" /tmp/research_strategy_recommendation_engine_plan_v1.out
grep -q "RECOMMENDATION_METRIC name=recommendation_score" /tmp/research_strategy_recommendation_engine_plan_v1.out
grep -q "PROMOTION_STATUS code=MICRO_LIVE_CANDIDATE" /tmp/research_strategy_recommendation_engine_plan_v1.out
grep -q "contract=engine_never_enables_strategy_directly" /tmp/research_strategy_recommendation_engine_plan_v1.out
grep -q "rule=state_edge_candidate_required_before_strategy_recommendation" /tmp/research_strategy_recommendation_engine_plan_v1.out
grep -q "rule=promotion_gate_cannot_enable_runtime" /tmp/research_strategy_recommendation_engine_plan_v1.out
grep -q "rule=no_runtime_execution_changes" /tmp/research_strategy_recommendation_engine_plan_v1.out
grep -q "VERDICT=RESEARCH_STRATEGY_RECOMMENDATION_ENGINE_PLAN_READY" /tmp/research_strategy_recommendation_engine_plan_v1.out

echo "TEST_RESEARCH_STRATEGY_RECOMMENDATION_ENGINE_PLAN_V1_OK"
