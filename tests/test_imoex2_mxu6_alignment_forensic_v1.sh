#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST IMOEX2 MXU6 ALIGNMENT FORENSIC V1 ==="

python -m py_compile \
  src/scripts/research/build_imoex2_mxu6_alignment_forensic_v1.py

OUTPUT="$(
  PYTHONPATH=src \
  python src/scripts/research/build_imoex2_mxu6_alignment_forensic_v1.py
)"

echo "$OUTPUT"

grep -q 'signal_symbol=IMOEX2' <<< "$OUTPUT"
grep -q 'execution_symbol=MXU6@RTSX' <<< "$OUTPUT"

grep -q 'SUMMARY_ROW' <<< "$OUTPUT"
grep -q 'REASON_ROWS' <<< "$OUTPUT"
grep -q 'MISSING_DATE_ROWS' <<< "$OUTPUT"
grep -q 'MISSING_HOUR_ROWS' <<< "$OUTPUT"

grep -q 'reason=FULL_ALIGNMENT' <<< "$OUTPUT"
grep -q 'reason=MISSING_ENTRY_BAR' <<< "$OUTPUT"
grep -q 'reason=MISSING_EXIT_BAR' <<< "$OUTPUT"
grep -q 'reason=MISSING_ENTRY_AND_EXIT' <<< "$OUTPUT"

grep -q 'economic_verdict_allowed=0' <<< "$OUTPUT"
grep -q 'db_writes_performed=0' <<< "$OUTPUT"
grep -q 'runtime_changed=0' <<< "$OUTPUT"
grep -q 'execution_changed=0' <<< "$OUTPUT"
grep -q 'orders_changed=0' <<< "$OUTPUT"
grep -q 'fills_changed=0' <<< "$OUTPUT"
grep -q 'micro_live_allowed=0' <<< "$OUTPUT"

grep -Eq \
'VERDICT=IMOEX2_MXU6_ALIGNMENT_FORENSIC_(DIRECT_REPLAY_READY|CALENDAR_MAPPING_REQUIRED)' \
<<< "$OUTPUT"

echo
echo "=== DIFF CHECK ==="
git diff --check

echo
echo "=== WORKTREE ==="
git status --short

echo
echo \
"VERDICT=TEST_IMOEX2_MXU6_ALIGNMENT_FORENSIC_V1_OK"
