#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_RESEARCH_CANONICAL_SCHEMA_PLAN_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_research_canonical_schema_plan_v1.py

src/scripts/research/build_research_canonical_schema_plan_v1.py \
  | tee /tmp/research_canonical_schema_plan_v1.out

grep -q "TABLE name=research_market_bars_v1" /tmp/research_canonical_schema_plan_v1.out
grep -q "TABLE name=research_trade_facts_v1" /tmp/research_canonical_schema_plan_v1.out
grep -q "TABLE name=research_trade_feature_snapshots_v1" /tmp/research_canonical_schema_plan_v1.out
grep -q "TABLE name=research_market_state_context_v1" /tmp/research_canonical_schema_plan_v1.out
grep -q "VERDICT=RESEARCH_CANONICAL_SCHEMA_PLAN_READY" /tmp/research_canonical_schema_plan_v1.out

echo "TEST_RESEARCH_CANONICAL_SCHEMA_PLAN_V1_OK"
