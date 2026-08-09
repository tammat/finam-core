#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST IMOEX2 MXU6 COMMON CALENDAR V1 ==="

python -m py_compile \
  src/scripts/research/build_imoex2_mxu6_common_calendar_v1.py

OUTPUT="$(
  PYTHONPATH=src \
  python src/scripts/research/build_imoex2_mxu6_common_calendar_v1.py
)"

echo "$OUTPUT"

grep -q 'SUMMARY_ROW' <<< "$OUTPUT"
grep -q 'COMMON_DAY_ROWS' <<< "$OUTPUT"
grep -q 'economic_verdict_allowed=0' <<< "$OUTPUT"
grep -q 'db_writes_performed=0' <<< "$OUTPUT"
grep -q 'runtime_changed=0' <<< "$OUTPUT"
grep -q 'execution_changed=0' <<< "$OUTPUT"
grep -q 'micro_live_allowed=0' <<< "$OUTPUT"

grep -Eq \
'VERDICT=IMOEX2_MXU6_COMMON_CALENDAR_(READY|EMPTY)' \
<<< "$OUTPUT"

echo
echo "=== DIFF CHECK ==="
git diff --check

echo
echo "=== WORKTREE ==="
git status --short

echo
echo "VERDICT=TEST_IMOEX2_MXU6_COMMON_CALENDAR_V1_OK"
