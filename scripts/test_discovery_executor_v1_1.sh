#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_DISCOVERY_EXECUTOR_V1_1 ==="

PYTHONPATH=src src/scripts/research/build_discovery_executor_v1_1.py \
  | tee /tmp/discovery_executor_v1_1.out

grep -q "DISCOVERY_EXECUTOR_V1_1" /tmp/discovery_executor_v1_1.out
grep -q "registry=DiscoveryRegistry" /tmp/discovery_executor_v1_1.out
grep -q "plugins=PostgresDiscovery,PythonDiscovery,BashDiscovery,SystemdDiscovery" /tmp/discovery_executor_v1_1.out
grep -q "source_count=PostgresDiscovery:" /tmp/discovery_executor_v1_1.out
grep -q "source_count=PythonDiscovery:" /tmp/discovery_executor_v1_1.out
grep -q "source_count=BashDiscovery:" /tmp/discovery_executor_v1_1.out
grep -q "source_count=SystemdDiscovery:" /tmp/discovery_executor_v1_1.out
grep -q "executor_policy=DEDUP_BY_OBJECT_ID" /tmp/discovery_executor_v1_1.out
grep -q "catalog_write_deferred=1" /tmp/discovery_executor_v1_1.out
grep -q "runtime_changed=0" /tmp/discovery_executor_v1_1.out
grep -q "execution_changed=0" /tmp/discovery_executor_v1_1.out
grep -q "orders_changed=0" /tmp/discovery_executor_v1_1.out
grep -q "fills_changed=0" /tmp/discovery_executor_v1_1.out
grep -q "micro_live_allowed=0" /tmp/discovery_executor_v1_1.out
grep -q "VERDICT=DISCOVERY_EXECUTOR_V1_1_READY" /tmp/discovery_executor_v1_1.out

echo "TEST_DISCOVERY_EXECUTOR_V1_1_OK"
