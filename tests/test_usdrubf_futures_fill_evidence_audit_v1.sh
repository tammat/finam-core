#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1
export PYTHONPATH=src

SCRIPT=src/scripts/research/build_usdrubf_futures_fill_evidence_audit_v1.py

echo "=== TEST_USDRUBF_FUTURES_FILL_EVIDENCE_AUDIT_V1 ==="

OUTPUT="$(
python "$SCRIPT"
)"

printf '%s\n' "$OUTPUT"

grep -q \
'^SOURCE_CONTRACT schema=analytics table=v_futures_fill_evidence_verified_v1 ' \
<<< "$OUTPUT"

grep -q \
'^RESOLVED_COLUMNS symbol=symbol timestamp=execution_ts quantity=quantity_contracts price=price$' \
<<< "$OUTPUT"

grep -q \
'^usdrubf_verified_fill_symbols=0$' \
<<< "$OUTPUT"

grep -q \
'^commission_overlap_days=0$' \
<<< "$OUTPUT"

grep -q \
'^commission_overlap_contracts=0$' \
<<< "$OUTPUT"

grep -q \
'^evidence_status=USDRUBF_VERIFIED_FILLS_NOT_AVAILABLE$' \
<<< "$OUTPUT"

grep -q '^db_writes_performed=0$' <<< "$OUTPUT"
grep -q '^runtime_changed=0$' <<< "$OUTPUT"
grep -q '^execution_changed=0$' <<< "$OUTPUT"
grep -q '^orders_changed=0$' <<< "$OUTPUT"
grep -q '^fills_changed=0$' <<< "$OUTPUT"
grep -q '^economic_edge_claimed=0$' <<< "$OUTPUT"
grep -q '^micro_live_allowed=0$' <<< "$OUTPUT"

grep -q \
'^VERDICT=USDRUBF_FUTURES_FILL_EVIDENCE_AUDIT_V1_READY$' \
<<< "$OUTPUT"

echo "actual_usdrubf_fill_evidence=0"
echo "actual_usdrubf_commission_evidence=0"
echo "fallback_fee_model_required=1"
echo "economic_edge_claimed=0"
echo "micro_live_allowed=0"

echo "VERDICT=TEST_USDRUBF_FUTURES_FILL_EVIDENCE_AUDIT_V1_OK"
