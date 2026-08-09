#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST GOLD UP REGIME FROZEN OOS V1 ==="

python -m py_compile \
  src/scripts/research/build_gold_up_regime_frozen_oos_v1.py

OUTPUT="$(
  PYTHONPATH=src \
  python src/scripts/research/build_gold_up_regime_frozen_oos_v1.py
)"

echo "$OUTPUT"

grep -q 'development_rows_allowed=0' <<< "$OUTPUT"
grep -q 'regime_rule=SMA20_GT_SMA50' <<< "$OUTPUT"
grep -q 'exit_model=MARKET_BARS_M5_NEXT_10' <<< "$OUTPUT"
grep -q 'runtime_allow=0' <<< "$OUTPUT"
grep -q 'execution_enabled=0' <<< "$OUTPUT"

grep -Eq \
'VERDICT=GOLD_UP_REGIME_OOS_(ACCUMULATING|PASS|FAIL)' \
<<< "$OUTPUT"

echo
echo "=== DIFF CHECK ==="
git diff --check

echo
echo "VERDICT=TEST_GOLD_UP_REGIME_FROZEN_OOS_V1_OK"
