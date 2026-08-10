#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1
export PYTHONPATH=src

echo "=== TEST_NET_FIRST_SHADOW_COVERAGE_V1 ==="

OUTPUT="$(
python \
src/scripts/research/build_net_first_shadow_coverage_v1.py
)"

printf '%s\n' "$OUTPUT"

grep -q '^total_candidates=27$' <<< "$OUTPUT"
grep -q '^economically_resolved=27$' <<< "$OUTPUT"
grep -q '^would_admit=18$' <<< "$OUTPUT"
grep -q '^would_reject=9$' <<< "$OUTPUT"
grep -q '^economic_reject_rate_pct=33.3333$' <<< "$OUTPUT"
grep -q '^potential_downstream_saved=9$' <<< "$OUTPUT"
grep -q '^economic_coverage_pct=100.0000$' <<< "$OUTPUT"

grep -q '^shadow_admission_validated=1$' <<< "$OUTPUT"
grep -q '^enforced_admission_enabled=0$' <<< "$OUTPUT"
grep -q '^production_pipeline_changed=0$' <<< "$OUTPUT"

grep -q '^runtime_changed=0$' <<< "$OUTPUT"
grep -q '^execution_changed=0$' <<< "$OUTPUT"
grep -q '^orders_changed=0$' <<< "$OUTPUT"
grep -q '^fills_changed=0$' <<< "$OUTPUT"
grep -q '^micro_live_allowed=0$' <<< "$OUTPUT"

grep -q \
'^VERDICT=NET_FIRST_SHADOW_COVERAGE_V1_OK$' \
<<< "$OUTPUT"

echo \
"VERDICT=TEST_NET_FIRST_SHADOW_COVERAGE_V1_OK"
