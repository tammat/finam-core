#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_GOLD_FILTERED_RESEARCH_ONLY_DECISION_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_gold_filtered_research_only_decision_v1.py

src/scripts/research/build_gold_filtered_research_only_decision_v1.py \
  | tee /tmp/gold_filtered_research_only_decision_v1.out

grep -q "decision=KEEP_RESEARCH_ONLY" \
  /tmp/gold_filtered_research_only_decision_v1.out

grep -q "runtime_candidate=forbidden" \
  /tmp/gold_filtered_research_only_decision_v1.out

grep -q "day_wide_anomaly=1" \
  /tmp/gold_filtered_research_only_decision_v1.out

grep -q "VERDICT=GOLD_FILTERED_RESEARCH_ONLY_DECISION_READY" \
  /tmp/gold_filtered_research_only_decision_v1.out

echo "TEST_GOLD_FILTERED_RESEARCH_ONLY_DECISION_V1_OK"
