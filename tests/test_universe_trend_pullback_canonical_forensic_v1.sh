#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo \
"=== TEST UNIVERSE TREND PULLBACK CANONICAL FORENSIC V1 ==="

python -m py_compile \
  src/scripts/research/build_universe_trend_pullback_canonical_forensic_v1.py

OUTPUT="$(
  PYTHONPATH=src \
  python \
    src/scripts/research/build_universe_trend_pullback_canonical_forensic_v1.py
)"

echo "$OUTPUT"

grep -q \
  'mode=canonical_true_gross_forensic' \
  <<< "$OUTPUT"

grep -q \
  'canonical_adapter_used=1' \
  <<< "$OUTPUT"

grep -q \
  'generic_execution_runner_used=0' \
  <<< "$OUTPUT"

grep -q \
  'signal_metric_source=GROSS_PNL' \
  <<< "$OUTPUT"

grep -q 'FORENSIC_ROW' <<< "$OUTPUT"
grep -q 'FOLD_ROW' <<< "$OUTPUT"

grep -q \
  'chronological_folds_used=1' \
  <<< "$OUTPUT"

grep -q \
  'fold_boundary_crossing_excluded=1' \
  <<< "$OUTPUT"

grep -q \
  'multiple_testing_adjusted=1' \
  <<< "$OUTPUT"

grep -q \
  'multiple_testing_trials=5' \
  <<< "$OUTPUT"

grep -q \
  'parameter_search_performed=0' \
  <<< "$OUTPUT"

grep -q \
  'execution_costs_used=0' \
  <<< "$OUTPUT"

grep -q \
  'db_writes_performed=0' \
  <<< "$OUTPUT"

grep -q 'runtime_changed=0' <<< "$OUTPUT"
grep -q 'execution_changed=0' <<< "$OUTPUT"
grep -q 'orders_changed=0' <<< "$OUTPUT"
grep -q 'fills_changed=0' <<< "$OUTPUT"
grep -q 'micro_live_allowed=0' <<< "$OUTPUT"

grep -Eq \
'VERDICT=UNIVERSE_TREND_PULLBACK_CANONICAL_FORENSIC_(CANDIDATES_SURVIVE|NO_CANDIDATES_SURVIVE)' \
<<< "$OUTPUT"

echo
echo "=== BASELINE CANDIDATE CONTRACT ==="

grep -q \
  'SUMMARY_ROW trials=5 preliminary_candidates=4' \
  <<< "$OUTPUT"

echo \
"VERDICT=TREND_PULLBACK_CANONICAL_BASELINE_CANDIDATES_REPRODUCED"

echo
echo "=== DIFF CHECK ==="
git diff --check

echo
echo "=== WORKTREE ==="
git status --short

echo
echo \
"VERDICT=TEST_UNIVERSE_TREND_PULLBACK_CANONICAL_FORENSIC_V1_OK"
