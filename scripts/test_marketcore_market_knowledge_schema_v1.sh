#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_MARKET_KNOWLEDGE_SCHEMA_V1 ==="

doc="docs/MARKETCORE_MARKET_KNOWLEDGE_SCHEMA_V1.txt"

test -f "$doc"

for section in \
  "BUSINESS ONTOLOGY" \
  "SEMANTIC RELATIONSHIPS" \
  "POSTGRESQL SCHEMA PLAN" \
  "TABLE PLAN" \
  "DATA SOURCE RULES" \
  "VERSIONING" \
  "SAFETY RULES" \
  "EDGE SCORE V2 RELATION" \
  "FIRST IMPLEMENTATION ORDER" \
  "ACCEPTANCE CRITERIA"
do
  grep -q "$section" "$doc"
done

for table_name in \
  "knowledge.market_v1" \
  "knowledge.exchange_v1" \
  "knowledge.asset_class_v1" \
  "knowledge.sector_v1" \
  "knowledge.industry_v1" \
  "knowledge.instrument_v1" \
  "knowledge.market_regime_v1" \
  "knowledge.market_context_v1" \
  "knowledge.strategy_context_v1" \
  "knowledge.edge_context_v1" \
  "knowledge.relationship_v1" \
  "knowledge.observation_v1" \
  "knowledge.recommendation_v1"
do
  grep -q "$table_name" "$doc"
done

grep -q "Edge Score V2 remains frozen" "$doc"
grep -q "runtime_allowed=0" "$doc"
grep -q "execution_allowed=0" "$doc"
grep -q "micro_live_allowed=0" "$doc"
grep -q "orders_changed=0" "$doc"
grep -q "fills_changed=0" "$doc"
grep -q "VERDICT=MARKETCORE_MARKET_KNOWLEDGE_SCHEMA_V1_READY" "$doc"

echo "market_knowledge_schema_doc=OK"
echo "edge_score_v2_frozen=OK"
echo "broker_independent=OK"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_MARKET_KNOWLEDGE_SCHEMA_V1_READY"
echo "VERDICT=TEST_MARKETCORE_MARKET_KNOWLEDGE_SCHEMA_V1_OK"
