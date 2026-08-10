#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1
export PYTHONPATH=src

SCRIPT=src/scripts/research/run_trade_level_real_shadow_admission_v1.py

echo "=== TEST_TRADE_LEVEL_REAL_SHADOW_ADMISSION_V1 ==="

OUTPUT="$(python "$SCRIPT")"

printf '%s\n' "$OUTPUT"

grep -q '^trade_level_candidates=9$' <<< "$OUTPUT"
grep -q '^would_admit=3$' <<< "$OUTPUT"
grep -q '^would_reject=6$' <<< "$OUTPUT"

ROWS="$(
grep -c '^TRADE_LEVEL_SHADOW_ROW ' \
<<< "$OUTPUT"
)"

[ "$ROWS" -eq 9 ]

REJECTS="$(
grep -c \
'decision=WOULD_REJECT' \
<<< "$OUTPUT"
)"

ADMITS="$(
grep -c \
'decision=WOULD_ADMIT' \
<<< "$OUTPUT"
)"

[ "$REJECTS" -eq 6 ]
[ "$ADMITS" -eq 3 ]

grep -q \
'^individual_trade_rows_used=1$' \
<<< "$OUTPUT"

grep -q \
'^persisted_trade_cost_evidence_used=1$' \
<<< "$OUTPUT"

grep -q \
'^aggregate_observation_costs_used=0$' \
<<< "$OUTPUT"

grep -q \
'^strategy_reconstruction_required=0$' \
<<< "$OUTPUT"

grep -q '^enforced_admission_enabled=0$' <<< "$OUTPUT"
grep -q '^production_pipeline_changed=0$' <<< "$OUTPUT"
grep -q '^runtime_changed=0$' <<< "$OUTPUT"
grep -q '^execution_changed=0$' <<< "$OUTPUT"
grep -q '^orders_changed=0$' <<< "$OUTPUT"
grep -q '^fills_changed=0$' <<< "$OUTPUT"
grep -q '^micro_live_allowed=0$' <<< "$OUTPUT"

grep -q \
'^VERDICT=TRADE_LEVEL_REAL_SHADOW_ADMISSION_V1_READY$' \
<<< "$OUTPUT"

echo \
"VERDICT=TEST_TRADE_LEVEL_REAL_SHADOW_ADMISSION_V1_OK"
