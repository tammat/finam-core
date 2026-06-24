#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_EDGE_BREAKDOWN_CAUSE_AUDIT_V1 ==="

python3 -m py_compile src/scripts/research/build_edge_breakdown_cause_audit_v1.py

src/scripts/research/build_edge_breakdown_cause_audit_v1.py \
  | tee /tmp/edge_breakdown_cause_audit_v1.out

grep -q "EDGE_BREAKDOWN_CAUSE_AUDIT_V1" /tmp/edge_breakdown_cause_audit_v1.out
grep -q "CAUSE_ROW symbol=GDU6@RTSX" /tmp/edge_breakdown_cause_audit_v1.out
grep -q "CAUSE_ROW symbol=GLU6@RTSX" /tmp/edge_breakdown_cause_audit_v1.out
grep -q "CAUSE_ROW symbol=NGM6@RTSX" /tmp/edge_breakdown_cause_audit_v1.out
grep -q "probable_cause=" /tmp/edge_breakdown_cause_audit_v1.out
grep -q "VERDICT=EDGE_BREAKDOWN_CAUSE_AUDIT_READY" /tmp/edge_breakdown_cause_audit_v1.out

echo "TEST_EDGE_BREAKDOWN_CAUSE_AUDIT_V1_OK"
