#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1
export PYTHONPATH=src

SCRIPT=src/scripts/research/run_verified_net_real_shadow_admission_v1.py

echo "=== TEST_VERIFIED_NET_REAL_SHADOW_ADMISSION_V1 ==="

OUTPUT="$(python "$SCRIPT")"

printf '%s\n' "$OUTPUT"

grep -q '^verified_net_candidates=16$' <<< "$OUTPUT"
grep -q '^would_admit=14$' <<< "$OUTPUT"
grep -q '^would_reject=2$' <<< "$OUTPUT"
grep -q '^oos_fail=16$' <<< "$OUTPUT"

REJECT_ROWS="$(
grep -c \
'decision=WOULD_REJECT economic_status=REJECT_INSUFFICIENT_TRADES' \
<<< "$OUTPUT"
)"

[ "$REJECT_ROWS" -eq 2 ]

ADMIT_ROWS="$(
grep -c \
'decision=WOULD_ADMIT economic_status=PASS' \
<<< "$OUTPUT"
)"

[ "$ADMIT_ROWS" -eq 14 ]

grep -q '^aggregate_net_metrics_used=1$' <<< "$OUTPUT"
grep -q '^synthetic_trade_reconstruction_used=0$' <<< "$OUTPUT"

grep -q '^shadow_admission_enabled=1$' <<< "$OUTPUT"
grep -q '^enforced_admission_enabled=0$' <<< "$OUTPUT"
grep -q '^production_pipeline_changed=0$' <<< "$OUTPUT"

grep -q '^runtime_changed=0$' <<< "$OUTPUT"
grep -q '^execution_changed=0$' <<< "$OUTPUT"
grep -q '^orders_changed=0$' <<< "$OUTPUT"
grep -q '^fills_changed=0$' <<< "$OUTPUT"
grep -q '^micro_live_allowed=0$' <<< "$OUTPUT"

grep -q \
'^VERDICT=VERIFIED_NET_REAL_SHADOW_ADMISSION_V1_READY$' \
<<< "$OUTPUT"

echo "verified_net_candidates=16"
echo "economic_gate_saved_oos_candidates=2"
echo "economic_gate_admitted_to_oos=14"
echo "oos_rejected_after_economic_pass=14"

echo \
"VERDICT=TEST_VERIFIED_NET_REAL_SHADOW_ADMISSION_V1_OK"
