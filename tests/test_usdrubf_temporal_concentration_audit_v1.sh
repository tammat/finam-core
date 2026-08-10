#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST USDRUBF TEMPORAL CONCENTRATION AUDIT V1 ==="

python -m py_compile \
  src/scripts/research/build_usdrubf_temporal_concentration_audit_v1.py

OUTPUT="$(
  PYTHONPATH=src \
  python \
    src/scripts/research/build_usdrubf_temporal_concentration_audit_v1.py
)"

echo "$OUTPUT"

grep -q \
  'mode=read_only_temporal_forensic' \
  <<< "$OUTPUT"

grep -q \
  'symbol=USDRUBF@RTSX' \
  <<< "$OUTPUT"

grep -q \
  'CANDIDATE_CONCENTRATION_ROW' \
  <<< "$OUTPUT"

grep -q \
  'TEMPORAL_FOLD_ROW' \
  <<< "$OUTPUT"

grep -q \
  'parameter_search_performed=0' \
  <<< "$OUTPUT"

grep -q \
  'economic_edge_claimed=0' \
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
'VERDICT=USDRUBF_TEMPORAL_CONCENTRATION_(DETECTED|NOT_DETECTED)' \
<<< "$OUTPUT"

echo
echo "=== DIFF CHECK ==="
git diff --check

echo
echo "=== WORKTREE ==="
git status --short

echo \
"VERDICT=TEST_USDRUBF_TEMPORAL_CONCENTRATION_AUDIT_V1_OK"
