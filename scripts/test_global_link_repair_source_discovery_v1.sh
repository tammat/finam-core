#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_GLOBAL_LINK_REPAIR_SOURCE_DISCOVERY_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_global_link_repair_source_discovery_v1.py

src/scripts/research/build_global_link_repair_source_discovery_v1.py \
  | tee /tmp/global_link_repair_source_discovery_v1.out

grep -q "GLOBAL_LINK_REPAIR_SOURCE_DISCOVERY_V1" /tmp/global_link_repair_source_discovery_v1.out
grep -q "CANDIDATE_SOURCE_TABLES" /tmp/global_link_repair_source_discovery_v1.out
grep -q "TARGET_COVERAGE" /tmp/global_link_repair_source_discovery_v1.out
grep -q "TARGET symbol=NGN6@RTSX" /tmp/global_link_repair_source_discovery_v1.out
grep -q "TARGET symbol=BRN6@RTSX" /tmp/global_link_repair_source_discovery_v1.out
grep -q "usable_sources=" /tmp/global_link_repair_source_discovery_v1.out
grep -Eq "VERDICT=GLOBAL_LINK_REPAIR_SOURCE_DISCOVERY_SOURCE_FOUND|VERDICT=GLOBAL_LINK_REPAIR_SOURCE_DISCOVERY_NO_SOURCE" /tmp/global_link_repair_source_discovery_v1.out

echo "TEST_GLOBAL_LINK_REPAIR_SOURCE_DISCOVERY_V1_OK"
