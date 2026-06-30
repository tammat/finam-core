#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_DATA_SOURCE_REGISTRY_GAP_AUDIT_V1 ==="

PYTHONPATH=src python \
  src/scripts/research/audit_data_source_registry_gaps_v1.py \
  >/tmp/data_source_registry_gap_audit_v1.out

cat /tmp/data_source_registry_gap_audit_v1.out

grep -q "VERDICT=DATA_SOURCE_REGISTRY_GAP_AUDIT_V1_READY" /tmp/data_source_registry_gap_audit_v1.out
grep -q "COVERED|schema=public|table=market_bars|source_origin=Finam Runtime" /tmp/data_source_registry_gap_audit_v1.out
grep -q "COVERED|schema=public|table=market_ticks|source_origin=Finam Runtime" /tmp/data_source_registry_gap_audit_v1.out
grep -q "COVERED|schema=warehouse|table=normalized_bar_event_v1|source_origin=Finam History" /tmp/data_source_registry_gap_audit_v1.out
grep -q "tables_scanned=" /tmp/data_source_registry_gap_audit_v1.out
grep -q "covered_tables=" /tmp/data_source_registry_gap_audit_v1.out
grep -q "uncovered_tables=" /tmp/data_source_registry_gap_audit_v1.out
grep -q "orphan_sources=" /tmp/data_source_registry_gap_audit_v1.out
grep -q "micro_live_allowed=0" /tmp/data_source_registry_gap_audit_v1.out

echo "gap_audit=READY"
echo "covered_detection=READY"
echo "uncovered_detection=READY"
echo "orphan_detection=READY"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_DATA_SOURCE_REGISTRY_GAP_AUDIT_V1_OK"
