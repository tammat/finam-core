#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST IMOEX2 EXECUTION MAPPING AUDIT V1 ==="

python -m py_compile \
  src/scripts/research/build_imoex2_execution_mapping_audit_v1.py

OUTPUT="$(
  PYTHONPATH=src \
  python src/scripts/research/build_imoex2_execution_mapping_audit_v1.py
)"

echo "$OUTPUT"

grep -q 'reference_symbol=IMOEX2' <<< "$OUTPUT"
grep -q 'execution_symbol=MXU6@RTSX' <<< "$OUTPUT"

grep -q 'REFERENCE_ROW symbol=IMOEX2' <<< "$OUTPUT"
grep -q 'EXECUTION_SERIES_ROW symbol=MXU6@RTSX' <<< "$OUTPUT"
grep -q 'INSTRUMENT_ROW symbol=MXU6@RTSX' <<< "$OUTPUT"

grep -q 'reference_ready=1' <<< "$OUTPUT"
grep -q 'execution_series_ready=1' <<< "$OUTPUT"
grep -q 'tradable_instrument_confirmed=1' <<< "$OUTPUT"
grep -q 'contract_spec_confirmed=1' <<< "$OUTPUT"
grep -q 'cost_spec_confirmed=1' <<< "$OUTPUT"
grep -q 'research_eligible=1' <<< "$OUTPUT"

grep -q 'db_writes_performed=0' <<< "$OUTPUT"
grep -q 'runtime_changed=0' <<< "$OUTPUT"
grep -q 'execution_changed=0' <<< "$OUTPUT"
grep -q 'orders_changed=0' <<< "$OUTPUT"
grep -q 'fills_changed=0' <<< "$OUTPUT"
grep -q 'micro_live_allowed=0' <<< "$OUTPUT"

grep -Eq \
'VERDICT=IMOEX2_EXECUTION_(MAPPING_CONFIRMED|PROXY_CONFIRMED_CANONICAL_LINK_PENDING)' \
<<< "$OUTPUT"

echo
echo "=== DIFF CHECK ==="
git diff --check

echo
echo "=== WORKTREE ==="
git status --short

echo
echo "VERDICT=TEST_IMOEX2_EXECUTION_MAPPING_AUDIT_V1_OK"
