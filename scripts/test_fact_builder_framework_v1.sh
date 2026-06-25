#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_FACT_BUILDER_FRAMEWORK_V1 ==="

PYTHONPATH=src src/scripts/research/build_fact_builder_framework_v1.py \
  | tee /tmp/fact_builder_framework_v1.out

grep -q "FACT_BUILDER_FRAMEWORK_V1" /tmp/fact_builder_framework_v1.out
grep -q "builder_name=NOOP_FACT_BUILDER_V1" /tmp/fact_builder_framework_v1.out
grep -q "fact_domain=WORKFLOW" /tmp/fact_builder_framework_v1.out
grep -q "fact_type=EVENT_FACT" /tmp/fact_builder_framework_v1.out
grep -q "result_status=PLANNED" /tmp/fact_builder_framework_v1.out
grep -q "result_reason=FACT_BUILDER_FRAMEWORK_READY" /tmp/fact_builder_framework_v1.out
grep -q "components=BuilderContext,BuilderResult,FactBuilder,BuilderRegistry,BuilderExecutor" /tmp/fact_builder_framework_v1.out
grep -q "builder_model=PLUGIN_BASED" /tmp/fact_builder_framework_v1.out
grep -q "workflow_event_builder_deferred=1" /tmp/fact_builder_framework_v1.out
grep -q "workflow_state_builder_deferred=1" /tmp/fact_builder_framework_v1.out
grep -q "market_trade_edge_deferred=1" /tmp/fact_builder_framework_v1.out
grep -q "runtime_changed=0" /tmp/fact_builder_framework_v1.out
grep -q "execution_changed=0" /tmp/fact_builder_framework_v1.out
grep -q "orders_changed=0" /tmp/fact_builder_framework_v1.out
grep -q "fills_changed=0" /tmp/fact_builder_framework_v1.out
grep -q "micro_live_allowed=0" /tmp/fact_builder_framework_v1.out
grep -q "VERDICT=FACT_BUILDER_FRAMEWORK_V1_READY" /tmp/fact_builder_framework_v1.out

echo "TEST_FACT_BUILDER_FRAMEWORK_V1_OK"
