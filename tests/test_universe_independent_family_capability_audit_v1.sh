#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo \
"=== TEST UNIVERSE INDEPENDENT FAMILY CAPABILITY AUDIT V1 ==="

python -m py_compile \
  src/scripts/research/build_universe_independent_family_capability_audit_v1.py

OUTPUT="$(
  PYTHONPATH=src \
  python \
    src/scripts/research/build_universe_independent_family_capability_audit_v1.py
)"

echo "$OUTPUT"

grep -q \
  'mode=read_only_capability_audit' \
  <<< "$OUTPUT"

grep -q 'FAMILY_SUMMARY_ROWS' \
  <<< "$OUTPUT"

grep -q 'CAPABILITY_ROWS' \
  <<< "$OUTPUT"

grep -q 'INDEPENDENT_FAMILY_ROWS' \
  <<< "$OUTPUT"

grep -q 'SUMMARY_ROW' \
  <<< "$OUTPUT"

grep -q \
  'independent_family_names=' \
  <<< "$OUTPUT"

grep -q \
  'parameter_search_performed=0' \
  <<< "$OUTPUT"

grep -q \
  'strategy_created=0' \
  <<< "$OUTPUT"

grep -q \
  'economic_edge_claimed=0' \
  <<< "$OUTPUT"

grep -q \
  'db_writes_performed=0' \
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

grep -q \
'VERDICT=UNIVERSE_INDEPENDENT_FAMILY_CAPABILITY_AUDIT_V1_READY' \
<<< "$OUTPUT"

echo
echo "=== BASELINE FAMILY CONTRACT ==="

for family in \
  MOMENTUM \
  MEAN_REVERSION \
  BREAKOUT
do
    grep -q \
      "FAMILY_SUMMARY_ROW family=${family} category=BASELINE_ALREADY_TESTED" \
      <<< "$OUTPUT"
done

echo \
"VERDICT=UNIVERSE_INDEPENDENT_FAMILY_BASELINE_CONTRACT_OK"

echo
echo "=== DIFF CHECK ==="
git diff --check

echo
echo "=== WORKTREE ==="
git status --short

echo
echo \
"VERDICT=TEST_UNIVERSE_INDEPENDENT_FAMILY_CAPABILITY_AUDIT_V1_OK"
