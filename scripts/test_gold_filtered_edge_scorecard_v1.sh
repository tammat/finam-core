#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_GOLD_FILTERED_EDGE_SCORECARD_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_gold_filtered_edge_scorecard_v1.py

src/scripts/research/build_gold_filtered_edge_scorecard_v1.py \
  | tee /tmp/gold_filtered_edge_scorecard_v1.out

grep -q "FILTERED_ROW symbol=GDU6@RTSX" /tmp/gold_filtered_edge_scorecard_v1.out
grep -q "FILTERED_ROW symbol=GLU6@RTSX" /tmp/gold_filtered_edge_scorecard_v1.out
grep -q "edge_mode=FILTERED_BEFORE_19_MSK" /tmp/gold_filtered_edge_scorecard_v1.out
grep -q "verdict=PRIMARY" /tmp/gold_filtered_edge_scorecard_v1.out
grep -q "VERDICT=GOLD_FILTERED_EDGE_SCORECARD_READY" /tmp/gold_filtered_edge_scorecard_v1.out

echo "TEST_GOLD_FILTERED_EDGE_SCORECARD_V1_OK"
