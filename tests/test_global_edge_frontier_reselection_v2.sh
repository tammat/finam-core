#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

PY="/opt/finam-core/venv/bin/python"
SCRIPT="src/scripts/research/build_global_edge_frontier_reselection_v2.py"

echo "=== TEST GLOBAL EDGE FRONTIER RESELECTION V2 ==="

PYTHONPATH=src "$PY" -m py_compile "$SCRIPT"

OUTPUT="$(
    PYTHONPATH=src "$PY" "$SCRIPT"
)"

printf '%s\n' "$OUTPUT"

grep -q '^FRONTIER_V2_ROW ' <<< "$OUTPUT"
grep -q '^active_challengers=' <<< "$OUTPUT"
grep -q '^target_candidates=' <<< "$OUTPUT"

grep -q \
'^ranking_dimensions=net,paired_gain,placebo,sample_maturity$' \
<<< "$OUTPUT"

grep -q '^physical_contract_segmentation_required=1$' \
<<< "$OUTPUT"

grep -q '^physical_contract_segmentation_materialized=0$' \
<<< "$OUTPUT"

grep -q '^db_writes_performed=0$' <<< "$OUTPUT"
grep -q '^production_pipeline_changed=0$' <<< "$OUTPUT"
grep -q '^thresholds_changed=0$' <<< "$OUTPUT"
grep -q '^net_first_logic_changed=0$' <<< "$OUTPUT"
grep -q '^runtime_changed=0$' <<< "$OUTPUT"
grep -q '^execution_changed=0$' <<< "$OUTPUT"
grep -q '^orders_changed=0$' <<< "$OUTPUT"
grep -q '^fills_changed=0$' <<< "$OUTPUT"
grep -q '^micro_live_allowed=0$' <<< "$OUTPUT"

grep -q \
'^VERDICT=GLOBAL_EDGE_FRONTIER_RESELECTION_V2_READY$' \
<<< "$OUTPUT"

echo "VERDICT=TEST_GLOBAL_EDGE_FRONTIER_RESELECTION_V2_OK"
