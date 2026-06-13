#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/scripts/runtime/build_lkoh_sell_only_review_gate_v1.py

python3 src/scripts/runtime/build_lkoh_sell_only_review_gate_v1.py \
  | tee /tmp/lkoh_sell_only_review_gate_v1.log

grep -q "LKOH SELL ONLY REVIEW GATE V1" /tmp/lkoh_sell_only_review_gate_v1.log
grep -q "REVIEW_GATE_ROW" /tmp/lkoh_sell_only_review_gate_v1.log
grep -q "decision=READY_FOR_RUNTIME_REVIEW" /tmp/lkoh_sell_only_review_gate_v1.log
grep -q "runtime_allowed=0" /tmp/lkoh_sell_only_review_gate_v1.log
grep -q "execution_enabled=0" /tmp/lkoh_sell_only_review_gate_v1.log
grep -q "LKOH_SELL_ONLY_REVIEW_GATE_V1_OK" /tmp/lkoh_sell_only_review_gate_v1.log

echo TEST_LKOH_SELL_ONLY_REVIEW_GATE_V1_OK
