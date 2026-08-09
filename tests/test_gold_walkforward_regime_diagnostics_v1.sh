#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST GOLD WALKFORWARD REGIME DIAGNOSTICS V1 ==="

python -m py_compile \
  src/scripts/research/build_gold_walkforward_regime_diagnostics_v1.py

OUTPUT="$(
    PYTHONPATH=src \
    python src/scripts/research/build_gold_walkforward_regime_diagnostics_v1.py
)"

echo "$OUTPUT"

grep -q \
  'exit_model=MARKET_BARS_M5_NEXT_10' \
  <<< "$OUTPUT"

grep -q \
  'cost_model=NOT_APPLIED_SOURCE_NOT_CONFIRMED' \
  <<< "$OUTPUT"

grep -q 'BUCKET_ROW bucket=1' <<< "$OUTPUT"
grep -q 'BUCKET_ROW bucket=2' <<< "$OUTPUT"
grep -q 'BUCKET_ROW bucket=3' <<< "$OUTPUT"
grep -q 'BUCKET_ROW bucket=4' <<< "$OUTPUT"

grep -q 'db_writes_performed=0' <<< "$OUTPUT"
grep -q 'runtime_allow=0' <<< "$OUTPUT"
grep -q 'execution_enabled=0' <<< "$OUTPUT"

grep -q \
  'VERDICT=GOLD_WALKFORWARD_REGIME_DIAGNOSTICS_READY' \
  <<< "$OUTPUT"

echo
echo "=== DIFF CHECK ==="
git diff --check

echo
echo "VERDICT=TEST_GOLD_WALKFORWARD_REGIME_DIAGNOSTICS_V1_OK"
