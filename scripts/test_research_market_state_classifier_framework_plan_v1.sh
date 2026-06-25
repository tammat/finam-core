#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_RESEARCH_MARKET_STATE_CLASSIFIER_FRAMEWORK_PLAN_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_research_market_state_classifier_framework_plan_v1.py

src/scripts/research/build_research_market_state_classifier_framework_plan_v1.py \
  | tee /tmp/research_market_state_classifier_framework_plan_v1.out

grep -q "RESEARCH_MARKET_STATE_CLASSIFIER_FRAMEWORK_PLAN_V1" /tmp/research_market_state_classifier_framework_plan_v1.out
grep -q "CLASSIFIER code=TrendClassifierV1" /tmp/research_market_state_classifier_framework_plan_v1.out
grep -q "CLASSIFIER code=VolatilityClassifierV1" /tmp/research_market_state_classifier_framework_plan_v1.out
grep -q "CLASSIFIER code=CompressionClassifierV1" /tmp/research_market_state_classifier_framework_plan_v1.out
grep -q "CLASSIFIER code=BreakoutClassifierV1" /tmp/research_market_state_classifier_framework_plan_v1.out
grep -q "CLASSIFIER code=SessionClassifierV1" /tmp/research_market_state_classifier_framework_plan_v1.out
grep -q "CLASSIFIER code=CorrelationClassifierV1" /tmp/research_market_state_classifier_framework_plan_v1.out
grep -q "contract=classifier_is_edge_blind" /tmp/research_market_state_classifier_framework_plan_v1.out
grep -q "rule=no_classifier_reads_pnl" /tmp/research_market_state_classifier_framework_plan_v1.out
grep -q "rule=rule_based_before_ml" /tmp/research_market_state_classifier_framework_plan_v1.out
grep -q "VERDICT=RESEARCH_MARKET_STATE_CLASSIFIER_FRAMEWORK_PLAN_READY" /tmp/research_market_state_classifier_framework_plan_v1.out

echo "TEST_RESEARCH_MARKET_STATE_CLASSIFIER_FRAMEWORK_PLAN_V1_OK"
