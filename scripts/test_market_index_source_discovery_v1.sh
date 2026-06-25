#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_MARKET_INDEX_SOURCE_DISCOVERY_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_market_index_source_discovery_v1.py

src/scripts/research/build_market_index_source_discovery_v1.py \
  | tee /tmp/market_index_source_discovery_v1.out

grep -q "MARKET_INDEX_SOURCE_DISCOVERY_V1" /tmp/market_index_source_discovery_v1.out
grep -q "INDEX_SOURCE_CANDIDATES" /tmp/market_index_source_discovery_v1.out
grep -q "INDEX_SYMBOL_PROBE" /tmp/market_index_source_discovery_v1.out
grep -q "usable_index_sources=" /tmp/market_index_source_discovery_v1.out
grep -q "next=MARKET_INDEX_SOURCE_DECISION_V1" /tmp/market_index_source_discovery_v1.out
grep -q "VERDICT=MARKET_INDEX_SOURCE_DISCOVERY_READY" /tmp/market_index_source_discovery_v1.out

echo "TEST_MARKET_INDEX_SOURCE_DISCOVERY_V1_OK"
