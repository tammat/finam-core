#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_TOP3_PAPER_RUNTIME_PREPARATION_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/scripts/research/build_top3_paper_runtime_preparation_v1.py

OUT="$(PYTHONPATH=src python src/scripts/research/build_top3_paper_runtime_preparation_v1.py)"

echo "$OUT"

echo "$OUT" | grep -q "mode=research_only"
echo "$OUT" | grep -q "prepared_rows=3"
echo "$OUT" | grep -q "preparation_status=PAPER_PREPARED"
echo "$OUT" | grep -q "runtime_allowed=0"
echo "$OUT" | grep -q "execution_allowed=0"
echo "$OUT" | grep -q "micro_live_allowed=0"
echo "$OUT" | grep -q "runtime_changed=0"
echo "$OUT" | grep -q "execution_changed=0"
echo "$OUT" | grep -q "orders_changed=0"
echo "$OUT" | grep -q "fills_changed=0"
echo "$OUT" | grep -q "VERDICT=TOP3_PAPER_RUNTIME_PREPARATION_V1_READY"

echo "VERDICT=TEST_TOP3_PAPER_RUNTIME_PREPARATION_V1_OK"
