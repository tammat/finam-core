#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_GLOBAL_LINK_REPAIR_PLAN_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_global_link_repair_plan_v1.py

src/scripts/research/build_global_link_repair_plan_v1.py \
  | tee /tmp/global_link_repair_plan_v1.out

grep -q "GLOBAL_LINK_REPAIR_PLAN_V1" /tmp/global_link_repair_plan_v1.out
grep -q "root_cause=NO_FEATURE_SNAPSHOT" /tmp/global_link_repair_plan_v1.out
grep -q "symbol=NGN6@RTSX" /tmp/global_link_repair_plan_v1.out
grep -q "symbol=BRN6@RTSX" /tmp/global_link_repair_plan_v1.out
grep -q "decision=BACKFILL_FEATURE_SNAPSHOTS_THEN_REBUILD_MARKET_STATES" /tmp/global_link_repair_plan_v1.out
grep -q "criterion=coverage>=0.90" /tmp/global_link_repair_plan_v1.out
grep -q "next=GLOBAL_LINK_REPAIR_SOURCE_DISCOVERY_V1" /tmp/global_link_repair_plan_v1.out
grep -q "VERDICT=GLOBAL_LINK_REPAIR_PLAN_READY" /tmp/global_link_repair_plan_v1.out

echo "TEST_GLOBAL_LINK_REPAIR_PLAN_V1_OK"
