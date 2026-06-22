#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_STABILITY_DATA_AUDIT_V1 ==="

python3 -m py_compile src/scripts/research/build_edge_stability_data_audit_v1.py

python3 src/scripts/research/build_edge_stability_data_audit_v1.py \
| tee /tmp/edge_stability_data_audit_v1.log

grep -q "VERDICT=EDGE_STABILITY_DATA_AUDIT_READY" /tmp/edge_stability_data_audit_v1.log
grep -q "TEST_EDGE_STABILITY_DATA_AUDIT_V1_OK" /tmp/edge_stability_data_audit_v1.log
grep -q "HAS_SOURCE_TS=1" /tmp/edge_stability_data_audit_v1.log
grep -q "HAS_STATUS=1" /tmp/edge_stability_data_audit_v1.log
grep -q "HAS_RETURN_PCT=1" /tmp/edge_stability_data_audit_v1.log

echo "VERDICT=EDGE_STABILITY_DATA_AUDIT_TEST_OK"
echo "TEST_EDGE_STABILITY_DATA_AUDIT_V1_OK"
