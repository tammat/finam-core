#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/analytics/build_runtime_governance_shadow_accumulation_v1.py

python3 \
  src/scripts/analytics/build_runtime_governance_shadow_accumulation_v1.py \
  | tee /tmp/runtime_governance_shadow_accumulation_v1.log

grep -q "RUNTIME GOVERNANCE SHADOW ACCUMULATION V1" \
  /tmp/runtime_governance_shadow_accumulation_v1.log

grep -q "ACCUMULATION_ROW" \
  /tmp/runtime_governance_shadow_accumulation_v1.log

grep -q "decision=WATCH_ONLY" \
  /tmp/runtime_governance_shadow_accumulation_v1.log

grep -q "RUNTIME_GOVERNANCE_SHADOW_ACCUMULATION_V1_OK" \
  /tmp/runtime_governance_shadow_accumulation_v1.log

echo TEST_RUNTIME_GOVERNANCE_SHADOW_ACCUMULATION_V1_OK
