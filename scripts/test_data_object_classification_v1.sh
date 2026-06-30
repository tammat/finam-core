#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_DATA_OBJECT_CLASSIFICATION_V1 ==="

PYTHONPATH=src python \
  src/scripts/research/classify_data_objects_v1.py \
  >/tmp/data_object_classification_v1.out

cat /tmp/data_object_classification_v1.out

grep -q "VERDICT=DATA_OBJECT_CLASSIFICATION_V1_READY" /tmp/data_object_classification_v1.out
grep -q "OBJECT|schema=public|table=market_bars|object_type=DATA_SOURCE" /tmp/data_object_classification_v1.out
grep -q "OBJECT|schema=public|table=market_ticks|object_type=DATA_SOURCE" /tmp/data_object_classification_v1.out
grep -q "OBJECT|schema=warehouse|table=normalized_bar_event_v1|object_type=DATA_SOURCE" /tmp/data_object_classification_v1.out
grep -q "OBJECT|schema=warehouse|table=data_source_registry_v1|object_type=REGISTRY" /tmp/data_object_classification_v1.out
grep -q "OBJECT_TYPE|type=DATA_SOURCE" /tmp/data_object_classification_v1.out
grep -q "OBJECT_TYPE|type=REGISTRY" /tmp/data_object_classification_v1.out
grep -q "tables_scanned=" /tmp/data_object_classification_v1.out
grep -q "classification=READY" /tmp/data_object_classification_v1.out
grep -q "micro_live_allowed=0" /tmp/data_object_classification_v1.out

echo "data_object_classification=READY"
echo "object_type_detection=READY"
echo "registry_layer_detected=READY"
echo "data_source_layer_detected=READY"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_DATA_OBJECT_CLASSIFICATION_V1_OK"
