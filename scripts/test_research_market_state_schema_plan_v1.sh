#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_RESEARCH_MARKET_STATE_SCHEMA_PLAN_V1 ==="

python3 -m py_compile \
src/scripts/research/build_research_market_state_schema_plan_v1.py

src/scripts/research/build_research_market_state_schema_plan_v1.py \
| tee /tmp/research_market_state_schema_plan_v1.out

grep -q "research.market_state_catalog_v1" /tmp/research_market_state_schema_plan_v1.out
grep -q "research.market_state_glossary_v1" /tmp/research_market_state_schema_plan_v1.out
grep -q "research.market_state_classifier_versions_v1" /tmp/research_market_state_schema_plan_v1.out
grep -q "research.market_state_snapshot_metadata_v1" /tmp/research_market_state_schema_plan_v1.out
grep -q "research.state_edge_scorecards_v1" /tmp/research_market_state_schema_plan_v1.out
grep -q "research.research_decisions_v1" /tmp/research_market_state_schema_plan_v1.out
grep -q "rule=no_table_without_business_purpose" /tmp/research_market_state_schema_plan_v1.out
grep -q "VERDICT=RESEARCH_MARKET_STATE_SCHEMA_PLAN_READY" /tmp/research_market_state_schema_plan_v1.out

echo "TEST_RESEARCH_MARKET_STATE_SCHEMA_PLAN_V1_OK"
