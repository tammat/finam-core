#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_TOP3_VALIDATION_EPIC_COMPLETE_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/scripts/research/build_top3_validation_epic_complete_v1.py

OUT=$(PYTHONPATH=src python src/scripts/research/build_top3_validation_epic_complete_v1.py)

echo "$OUT"

echo "$OUT" | grep -q "mode=epic_complete"
echo "$OUT" | grep -q "research_pipeline=COMPLETE"
echo "$OUT" | grep -q "top3_shadow_execution=COMPLETE"
echo "$OUT" | grep -q "top3_runtime_board=COMPLETE"
echo "$OUT" | grep -q "paper_ready=3"
echo "$OUT" | grep -q "runtime_allowed=0"
echo "$OUT" | grep -q "execution_allowed=0"
echo "$OUT" | grep -q "micro_live_allowed=0"
echo "$OUT" | grep -q "VERDICT=TOP3_VALIDATION_EPIC_COMPLETE"

echo "VERDICT=TEST_TOP3_VALIDATION_EPIC_COMPLETE_V1_OK"
