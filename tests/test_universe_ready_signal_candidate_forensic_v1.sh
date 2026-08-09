#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo \
"=== TEST UNIVERSE READY SIGNAL CANDIDATE FORENSIC V1 ==="

python -m py_compile \
  src/scripts/research/build_universe_ready_signal_candidate_forensic_v1.py

OUTPUT="$(
  PYTHONPATH=src \
  python \
    src/scripts/research/build_universe_ready_signal_candidate_forensic_v1.py
)"

echo "$OUTPUT"

grep -q 'mode=gross_candidate_forensic' \
  <<< "$OUTPUT"

grep -q 'FORENSIC_ROW' \
  <<< "$OUTPUT"

grep -q 'FOLD_ROW' \
  <<< "$OUTPUT"

grep -q \
  'multiple_testing_adjusted=1' \
  <<< "$OUTPUT"

grep -q \
  'chronological_folds_used=1' \
  <<< "$OUTPUT"

grep -q \
  'parameter_search_performed=0' \
  <<< "$OUTPUT"

grep -q \
  'economic_edge_claimed=0' \
  <<< "$OUTPUT"

grep -q 'execution_costs_used=0' \
  <<< "$OUTPUT"

grep -q 'db_writes_performed=0' \
  <<< "$OUTPUT"

grep -q 'runtime_changed=0' \
  <<< "$OUTPUT"

grep -q 'execution_changed=0' \
  <<< "$OUTPUT"

grep -q 'micro_live_allowed=0' \
  <<< "$OUTPUT"

grep -Eq \
'VERDICT=UNIVERSE_READY_SIGNAL_FORENSIC_(CANDIDATES_SURVIVE|NO_CANDIDATES_SURVIVE)' \
<<< "$OUTPUT"

echo
echo "=== DIFF CHECK ==="
git diff --check

echo
echo "=== WORKTREE ==="
git status --short

echo \
"VERDICT=TEST_UNIVERSE_READY_SIGNAL_CANDIDATE_FORENSIC_V1_OK"
