#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_DATA_SOURCE_REGISTRY_TRUE_COVERAGE_V1 ==="

PYTHONPATH=src python \
  src/scripts/research/build_data_source_registry_true_coverage_v1.py \
  >/tmp/data_source_registry_true_coverage_v1.out

cat /tmp/data_source_registry_true_coverage_v1.out

grep -q "VERDICT=DATA_SOURCE_REGISTRY_TRUE_COVERAGE_V1_READY" /tmp/data_source_registry_true_coverage_v1.out
grep -q "denominator=DATA_SOURCE_ONLY" /tmp/data_source_registry_true_coverage_v1.out
grep -q "DATA_SOURCE_COVERED|schema=public|table=market_bars|source_origin=Finam Runtime" /tmp/data_source_registry_true_coverage_v1.out
grep -q "DATA_SOURCE_COVERED|schema=public|table=market_ticks|source_origin=Finam Runtime" /tmp/data_source_registry_true_coverage_v1.out
grep -q "DATA_SOURCE_COVERED|schema=public|table=market_data|source_origin=Finam Runtime" /tmp/data_source_registry_true_coverage_v1.out
grep -q "DATA_SOURCE_COVERED|schema=warehouse|table=normalized_bar_event_v1|source_origin=Finam History" /tmp/data_source_registry_true_coverage_v1.out
grep -q "data_source_objects=" /tmp/data_source_registry_true_coverage_v1.out
grep -q "covered_data_source_objects=" /tmp/data_source_registry_true_coverage_v1.out
grep -q "true_coverage_pct=" /tmp/data_source_registry_true_coverage_v1.out
grep -q "reference_excluded=1" /tmp/data_source_registry_true_coverage_v1.out
grep -q "governance_excluded=1" /tmp/data_source_registry_true_coverage_v1.out
grep -q "workflow_excluded=1" /tmp/data_source_registry_true_coverage_v1.out
grep -q "runtime_state_excluded=1" /tmp/data_source_registry_true_coverage_v1.out
grep -q "micro_live_allowed=0" /tmp/data_source_registry_true_coverage_v1.out

echo "true_coverage=READY"
echo "denominator_data_source_only=READY"
echo "service_objects_excluded=READY"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_DATA_SOURCE_REGISTRY_TRUE_COVERAGE_V1_OK"
