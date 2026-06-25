#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_TRADE_FACTS_SOURCE_DISCOVERY_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_trade_facts_source_discovery_v1.py

src/scripts/research/build_trade_facts_source_discovery_v1.py \
  | tee /tmp/trade_facts_source_discovery_v1.out

grep -q "TRADE_FACTS_SOURCE_DISCOVERY_V1" /tmp/trade_facts_source_discovery_v1.out
grep -q "mode=discovery_read_only" /tmp/trade_facts_source_discovery_v1.out
grep -q "TABLE_DISCOVERY" /tmp/trade_facts_source_discovery_v1.out
grep -q "candidate_tables=" /tmp/trade_facts_source_discovery_v1.out
grep -q "research_trade_facts_exists=" /tmp/trade_facts_source_discovery_v1.out
grep -q "VERDICT=TRADE_FACTS_SOURCE_DISCOVERY_READY" /tmp/trade_facts_source_discovery_v1.out

echo "TEST_TRADE_FACTS_SOURCE_DISCOVERY_V1_OK"
