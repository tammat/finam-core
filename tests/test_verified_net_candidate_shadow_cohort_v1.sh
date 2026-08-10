#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1
export PYTHONPATH=src

SCRIPT=src/scripts/research/build_verified_net_candidate_shadow_cohort_v1.py

echo "=== TEST_VERIFIED_NET_CANDIDATE_SHADOW_COHORT_V1 ==="

OUTPUT="$(python "$SCRIPT")"

printf '%s\n' "$OUTPUT"

grep -q '^real_candidates=27$' \
<<< "$OUTPUT"

grep -q '^verified_net_candidates=16$' \
<<< "$OUTPUT"

grep -q '^cost_aware_promoted_candidates=1$' \
<<< "$OUTPUT"

grep -q '^replay_required_candidates=10$' \
<<< "$OUTPUT"

grep -q '^unsupported_candidates=0$' \
<<< "$OUTPUT"

grep -q '^phase_a_direct_gate_candidates=16$' \
<<< "$OUTPUT"

ROWS="$(
grep -c '^VERIFIED_NET_COHORT_ROW ' \
<<< "$OUTPUT"
)"

[ "$ROWS" -eq 16 ]

grep -q \
'^promoted_metrics_direct_gate_enabled=0$' \
<<< "$OUTPUT"

grep -q \
'^replay_required_direct_gate_enabled=0$' \
<<< "$OUTPUT"

grep -q '^db_writes_performed=0$' \
<<< "$OUTPUT"

grep -q '^runtime_changed=0$' \
<<< "$OUTPUT"

grep -q '^execution_changed=0$' \
<<< "$OUTPUT"

grep -q '^orders_changed=0$' \
<<< "$OUTPUT"

grep -q '^fills_changed=0$' \
<<< "$OUTPUT"

grep -q '^micro_live_allowed=0$' \
<<< "$OUTPUT"

grep -q \
'^VERDICT=VERIFIED_NET_CANDIDATE_SHADOW_COHORT_V1_READY$' \
<<< "$OUTPUT"

echo \
"VERDICT=TEST_VERIFIED_NET_CANDIDATE_SHADOW_COHORT_V1_OK"
