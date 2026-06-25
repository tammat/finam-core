#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_RESEARCH_MULTI_ASSET_BROKER_ARBITRAGE_SCHEMA_PLAN_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_research_multi_asset_broker_arbitrage_schema_plan_v1.py

src/scripts/research/build_research_multi_asset_broker_arbitrage_schema_plan_v1.py \
  | tee /tmp/research_multi_asset_broker_arbitrage_schema_plan_v1.out

grep -q "research.brokers_v1" /tmp/research_multi_asset_broker_arbitrage_schema_plan_v1.out
grep -q "research.exchanges_v1" /tmp/research_multi_asset_broker_arbitrage_schema_plan_v1.out
grep -q "research.instruments_v1" /tmp/research_multi_asset_broker_arbitrage_schema_plan_v1.out
grep -q "research.arbitrage_pairs_v1" /tmp/research_multi_asset_broker_arbitrage_schema_plan_v1.out
grep -q "VERDICT=RESEARCH_MULTI_ASSET_BROKER_ARBITRAGE_SCHEMA_PLAN_READY" /tmp/research_multi_asset_broker_arbitrage_schema_plan_v1.out

echo "TEST_RESEARCH_MULTI_ASSET_BROKER_ARBITRAGE_SCHEMA_PLAN_V1_OK"
