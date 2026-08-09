#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST IMOEX2 MXU6 COST SCALE AUDIT V1 ==="

python -m py_compile \
  src/scripts/research/build_imoex2_mxu6_cost_scale_audit_v1.py

OUTPUT="$(
  PYTHONPATH=src \
  python src/scripts/research/build_imoex2_mxu6_cost_scale_audit_v1.py
)"

echo "$OUTPUT"

grep -q 'signal_symbol=IMOEX2' <<< "$OUTPUT"
grep -q 'execution_symbol=MXU6@RTSX' <<< "$OUTPUT"

grep -q 'PRICE_SCALE_ROW' <<< "$OUTPUT"
grep -q 'ALIGNMENT_ROW' <<< "$OUTPUT"
grep -q 'COST_ROW' <<< "$OUTPUT"
grep -q 'DIAGNOSTIC_SCALE_ROW' <<< "$OUTPUT"

grep -q \
  'economic_verdict_allowed=0' \
  <<< "$OUTPUT"

grep -q 'db_writes_performed=0' <<< "$OUTPUT"
grep -q 'runtime_changed=0' <<< "$OUTPUT"
grep -q 'execution_changed=0' <<< "$OUTPUT"
grep -q 'micro_live_allowed=0' <<< "$OUTPUT"

grep -Eq \
'VERDICT=IMOEX2_MXU6_(DIRECT_COST_SCALE_SUPPORTED|RETURN_MAPPING_REQUIRED|PROXY_MAPPING_INSUFFICIENT)' \
<<< "$OUTPUT"

echo
echo "=== DIFF CHECK ==="
git diff --check

echo
echo "=== WORKTREE ==="
git status --short

echo
echo "VERDICT=TEST_IMOEX2_MXU6_COST_SCALE_AUDIT_V1_OK"
