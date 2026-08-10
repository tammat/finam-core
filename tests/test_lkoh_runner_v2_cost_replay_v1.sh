#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1
export PYTHONPATH=src

echo "=== TEST_LKOH_RUNNER_V2_COST_REPLAY_V1 ==="

OUTPUT="$(
python \
src/scripts/research/build_lkoh_runner_v2_cost_replay_v1.py
)"

printf '%s\n' "$OUTPUT"

grep -q 'trades=278' <<< "$OUTPUT"
grep -q 'gross_pnl=838.00000000' <<< "$OUTPUT"
grep -q 'net_pnl=189.097750000000' <<< "$OUTPUT"
grep -q 'decision=WOULD_ADMIT' <<< "$OUTPUT"
grep -q 'economic_status=PASS' <<< "$OUTPUT"

grep -q '^source_zero_cost_rows=278$' \
<<< "$OUTPUT"

grep -q '^reconstructed_cost_rows=278$' \
<<< "$OUTPUT"

grep -q \
'^legacy_v1_semantics_validated_before_v2_replay=1$' \
<<< "$OUTPUT"

grep -q '^runtime_changed=0$' <<< "$OUTPUT"
grep -q '^execution_changed=0$' <<< "$OUTPUT"
grep -q '^orders_changed=0$' <<< "$OUTPUT"
grep -q '^fills_changed=0$' <<< "$OUTPUT"
grep -q '^micro_live_allowed=0$' <<< "$OUTPUT"

grep -q \
'^VERDICT=LKOH_RUNNER_V2_COST_REPLAY_V1_READY$' \
<<< "$OUTPUT"

echo \
"VERDICT=TEST_LKOH_RUNNER_V2_COST_REPLAY_V1_OK"
