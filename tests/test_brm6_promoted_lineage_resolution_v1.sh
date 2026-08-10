#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1
export PYTHONPATH=src

echo "=== TEST_BRM6_PROMOTED_LINEAGE_RESOLUTION_V1 ==="

OUTPUT="$(
python \
src/scripts/research/build_brm6_promoted_lineage_resolution_v1.py
)"

printf '%s\n' "$OUTPUT"

grep -q '^oos_rows=2$' <<< "$OUTPUT"
grep -q '^observation_stale=1$' <<< "$OUTPUT"
grep -q '^candidate_matches_latest_oos=1$' <<< "$OUTPUT"

grep -q \
'^direct_promoted_metrics_allowed=0$' \
<<< "$OUTPUT"

grep -q \
'^chronological_cost_semantics_resolved=0$' \
<<< "$OUTPUT"

grep -q '^replay_required=1$' <<< "$OUTPUT"

grep -q \
'^lineage_status=STALE_PROMOTED_OBSERVATION$' \
<<< "$OUTPUT"

grep -q '^runtime_changed=0$' <<< "$OUTPUT"
grep -q '^execution_changed=0$' <<< "$OUTPUT"
grep -q '^orders_changed=0$' <<< "$OUTPUT"
grep -q '^fills_changed=0$' <<< "$OUTPUT"
grep -q '^micro_live_allowed=0$' <<< "$OUTPUT"

grep -q \
'^VERDICT=BRM6_PROMOTED_LINEAGE_RESOLUTION_V1_READY$' \
<<< "$OUTPUT"

echo \
"VERDICT=TEST_BRM6_PROMOTED_LINEAGE_RESOLUTION_V1_OK"
