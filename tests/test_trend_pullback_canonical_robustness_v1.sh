#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo \
"=== TEST TREND PULLBACK CANONICAL ROBUSTNESS V1 ==="

python -m py_compile \
  src/scripts/research/build_trend_pullback_canonical_robustness_v1.py

OUTPUT="$(
  PYTHONPATH=src \
  python \
    src/scripts/research/build_trend_pullback_canonical_robustness_v1.py
)"

echo "$OUTPUT"

grep -q \
  'mode=canonical_local_robustness' \
  <<< "$OUTPUT"

grep -q 'symbols=3' <<< "$OUTPUT"
grep -q 'variants=7' <<< "$OUTPUT"

for symbol in \
  'USDRUBF@RTSX' \
  'NVTK@MISX' \
  'PLZL@MISX'
do
    grep -q \
      "SYMBOL_ROBUSTNESS_ROW symbol=${symbol}" \
      <<< "$OUTPUT"
done

grep -q 'variant=BASELINE' <<< "$OUTPUT"
grep -q 'variant=FAST_MINUS' <<< "$OUTPUT"
grep -q 'variant=FAST_PLUS' <<< "$OUTPUT"
grep -q 'variant=SLOW_MINUS' <<< "$OUTPUT"
grep -q 'variant=SLOW_PLUS' <<< "$OUTPUT"
grep -q 'variant=PULLBACK_MINUS' <<< "$OUTPUT"
grep -q 'variant=PULLBACK_PLUS' <<< "$OUTPUT"

grep -q \
  'canonical_adapter_used=1' \
  <<< "$OUTPUT"

grep -q \
  'generic_execution_runner_used=0' \
  <<< "$OUTPUT"

grep -q \
  'signal_metric_source=GROSS_PNL' \
  <<< "$OUTPUT"

grep -q \
  'one_parameter_at_a_time=1' \
  <<< "$OUTPUT"

grep -q \
  'parameter_optimization_performed=0' \
  <<< "$OUTPUT"

grep -q \
  'chronological_folds_used=1' \
  <<< "$OUTPUT"

grep -q \
  'execution_costs_used=0' \
  <<< "$OUTPUT"

grep -q \
  'economic_edge_claimed=0' \
  <<< "$OUTPUT"

grep -q 'db_writes_performed=0' \
  <<< "$OUTPUT"
grep -q 'runtime_changed=0' \
  <<< "$OUTPUT"
grep -q 'execution_changed=0' \
  <<< "$OUTPUT"
grep -q 'orders_changed=0' \
  <<< "$OUTPUT"
grep -q 'fills_changed=0' \
  <<< "$OUTPUT"
grep -q 'micro_live_allowed=0' \
  <<< "$OUTPUT"

grep -Eq \
'VERDICT=TREND_PULLBACK_CANONICAL_ROBUSTNESS_(SURVIVORS_CONFIRMED|NO_SURVIVORS)' \
<<< "$OUTPUT"

echo
echo "=== TRIAL CONTRACT ==="

grep -q \
  'SUMMARY_ROW symbols=3 variants_per_symbol=7 trials=21' \
  <<< "$OUTPUT"

echo \
"VERDICT=TREND_PULLBACK_ROBUSTNESS_TRIAL_CONTRACT_OK"

echo
echo "=== DIFF CHECK ==="
git diff --check

echo
echo "=== WORKTREE ==="
git status --short

echo
echo \
"VERDICT=TEST_TREND_PULLBACK_CANONICAL_ROBUSTNESS_V1_OK"
