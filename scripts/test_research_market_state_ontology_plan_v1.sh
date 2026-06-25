#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_RESEARCH_MARKET_STATE_ONTOLOGY_PLAN_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_research_market_state_ontology_plan_v1.py

src/scripts/research/build_research_market_state_ontology_plan_v1.py \
  | tee /tmp/research_market_state_ontology_plan_v1.out

grep -q "RESEARCH_MARKET_STATE_ONTOLOGY_PLAN_V1" /tmp/research_market_state_ontology_plan_v1.out
grep -q "DOMAIN name=MARKET_STRUCTURE" /tmp/research_market_state_ontology_plan_v1.out
grep -q "STATE_GROUP domain=MARKET_STRUCTURE group=TREND" /tmp/research_market_state_ontology_plan_v1.out
grep -q "STATE_GROUP domain=PRICE_ACTION group=BREAKOUT" /tmp/research_market_state_ontology_plan_v1.out
grep -q "STATE_GROUP domain=SESSION group=SESSION_BUCKET" /tmp/research_market_state_ontology_plan_v1.out
grep -q "STATE_GROUP domain=DERIVATIVES group=EXPIRATION" /tmp/research_market_state_ontology_plan_v1.out
grep -q "STATE_GROUP domain=CORRELATION group=INTERMARKET_CONFIRMATION" /tmp/research_market_state_ontology_plan_v1.out
grep -q "rule=no_runtime_execution_changes" /tmp/research_market_state_ontology_plan_v1.out
grep -q "VERDICT=RESEARCH_MARKET_STATE_ONTOLOGY_PLAN_READY" /tmp/research_market_state_ontology_plan_v1.out

echo "TEST_RESEARCH_MARKET_STATE_ONTOLOGY_PLAN_V1_OK"
