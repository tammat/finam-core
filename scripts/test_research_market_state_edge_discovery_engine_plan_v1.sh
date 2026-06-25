#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_RESEARCH_MARKET_STATE_EDGE_DISCOVERY_ENGINE_PLAN_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_research_market_state_edge_discovery_engine_plan_v1.py

src/scripts/research/build_research_market_state_edge_discovery_engine_plan_v1.py \
  | tee /tmp/research_market_state_edge_discovery_engine_plan_v1.out

grep -q "RESEARCH_MARKET_STATE_EDGE_DISCOVERY_ENGINE_PLAN_V1" /tmp/research_market_state_edge_discovery_engine_plan_v1.out
grep -q "EDGE_STAGE order=1 code=DatasetSelector" /tmp/research_market_state_edge_discovery_engine_plan_v1.out
grep -q "EDGE_STAGE order=2 code=StateTradeLinker" /tmp/research_market_state_edge_discovery_engine_plan_v1.out
grep -q "EDGE_STAGE order=4 code=MetricCalculator" /tmp/research_market_state_edge_discovery_engine_plan_v1.out
grep -q "EDGE_STAGE order=6 code=BiasGuard" /tmp/research_market_state_edge_discovery_engine_plan_v1.out
grep -q "EDGE_METRIC name=profit_factor" /tmp/research_market_state_edge_discovery_engine_plan_v1.out
grep -q "EDGE_METRIC name=expectancy" /tmp/research_market_state_edge_discovery_engine_plan_v1.out
grep -q "EDGE_METRIC name=commission_drag" /tmp/research_market_state_edge_discovery_engine_plan_v1.out
grep -q "CANDIDATE_RULE name=positive_expectancy_required" /tmp/research_market_state_edge_discovery_engine_plan_v1.out
grep -q "EDGE_VERDICT code=MICRO_LIVE_CANDIDATE" /tmp/research_market_state_edge_discovery_engine_plan_v1.out
grep -q "contract=engine_never_promotes_to_runtime_directly" /tmp/research_market_state_edge_discovery_engine_plan_v1.out
grep -q "rule=trade_source_class_filter_required" /tmp/research_market_state_edge_discovery_engine_plan_v1.out
grep -q "rule=no_runtime_execution_changes" /tmp/research_market_state_edge_discovery_engine_plan_v1.out
grep -q "VERDICT=RESEARCH_MARKET_STATE_EDGE_DISCOVERY_ENGINE_PLAN_READY" /tmp/research_market_state_edge_discovery_engine_plan_v1.out

echo "TEST_RESEARCH_MARKET_STATE_EDGE_DISCOVERY_ENGINE_PLAN_V1_OK"
