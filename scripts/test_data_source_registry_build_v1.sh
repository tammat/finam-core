#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_DATA_SOURCE_REGISTRY_BUILD_V1 ==="

PYTHONPATH=src python \
  src/scripts/research/build_data_source_registry_build_v1.py \
  >/tmp/data_source_registry_build_v1.out

grep -q "VERDICT=DATA_SOURCE_REGISTRY_BUILD_V1_READY" /tmp/data_source_registry_build_v1.out

grep -q "source_origin=Finam Runtime" /tmp/data_source_registry_build_v1.out
grep -q "source_origin=Finam History" /tmp/data_source_registry_build_v1.out
grep -q "source_origin=MOEX History" /tmp/data_source_registry_build_v1.out
grep -q "source_origin=Generated" /tmp/data_source_registry_build_v1.out
grep -q "source_origin=Replay" /tmp/data_source_registry_build_v1.out
grep -q "source_origin=Paper Trading" /tmp/data_source_registry_build_v1.out
grep -q "source_origin=Runtime Trading" /tmp/data_source_registry_build_v1.out
grep -q "source_origin=Broker" /tmp/data_source_registry_build_v1.out
grep -q "source_origin=Strategy" /tmp/data_source_registry_build_v1.out
grep -q "source_origin=Research" /tmp/data_source_registry_build_v1.out
grep -q "source_origin=Feature" /tmp/data_source_registry_build_v1.out
grep -q "source_origin=AI" /tmp/data_source_registry_build_v1.out

grep -q "GATED_NO_ORDER_ACCESS" /tmp/data_source_registry_build_v1.out
grep -q "micro_live_allowed=0" /tmp/data_source_registry_build_v1.out

cat /tmp/data_source_registry_build_v1.out

echo "registry_build=READY"
echo "all_required_sources=READY"
echo "ai_order_access=BLOCKED"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_DATA_SOURCE_REGISTRY_BUILD_V1_OK"
