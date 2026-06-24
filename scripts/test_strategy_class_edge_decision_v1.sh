#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_STRATEGY_CLASS_EDGE_DECISION_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_strategy_class_edge_decision_v1.py

src/scripts/research/build_strategy_class_edge_decision_v1.py \
  | tee /tmp/strategy_class_edge_decision_v1.out

grep -q "CLASS_DECISION strategy_class=COMPRESSION_EXPANSION" /tmp/strategy_class_edge_decision_v1.out
grep -q "decision=WATCH_ONLY" /tmp/strategy_class_edge_decision_v1.out
grep -q "strategy_class=UNKNOWN" /tmp/strategy_class_edge_decision_v1.out
grep -q "decision=REJECT" /tmp/strategy_class_edge_decision_v1.out
grep -q "runtime_candidate=NONE" /tmp/strategy_class_edge_decision_v1.out
grep -q "VERDICT=STRATEGY_CLASS_EDGE_DECISION_READY" /tmp/strategy_class_edge_decision_v1.out

echo "TEST_STRATEGY_CLASS_EDGE_DECISION_V1_OK"
