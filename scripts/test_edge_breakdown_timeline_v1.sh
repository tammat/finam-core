#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_EDGE_BREAKDOWN_TIMELINE_V1 ==="

python3 -m py_compile src/scripts/research/build_edge_breakdown_timeline_v1.py

src/scripts/research/build_edge_breakdown_timeline_v1.py \
  | tee /tmp/edge_breakdown_timeline_v1.out

grep -q "EDGE_BREAKDOWN_TIMELINE_V1" /tmp/edge_breakdown_timeline_v1.out
grep -q "BREAKDOWN_ROW symbol=GDU6@RTSX" /tmp/edge_breakdown_timeline_v1.out
grep -q "BREAKDOWN_ROW symbol=GLU6@RTSX" /tmp/edge_breakdown_timeline_v1.out
grep -q "BREAKDOWN_ROW symbol=NGM6@RTSX" /tmp/edge_breakdown_timeline_v1.out
grep -q "TIMELINE_ROW symbol=GDU6@RTSX" /tmp/edge_breakdown_timeline_v1.out
grep -q "VERDICT=EDGE_BREAKDOWN_" /tmp/edge_breakdown_timeline_v1.out

echo "TEST_EDGE_BREAKDOWN_TIMELINE_V1_OK"
