#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

PY="/opt/finam-core/venv/bin/python"
SCRIPT="src/scripts/research/build_bru6_current_contract_neighborhood_search_v1.py"

echo "=== TEST BRU6 CURRENT CONTRACT NEIGHBORHOOD SEARCH V1 ==="

PYTHONPATH=src "$PY" -m py_compile "$SCRIPT"

OUTPUT="$(
    PYTHONPATH=src "$PY" "$SCRIPT"
)"

printf '%s\n' "$OUTPUT"

test "$(grep -c '^GRID_RESULT ' <<< "$OUTPUT")" -eq 5

grep -q '^source_bundles=24$' <<< "$OUTPUT"
grep -q '^completed_horizon_bundles=17$' <<< "$OUTPUT"

grep -q '^strategy=BR_CONSERVATIVE_BREAKOUT$' <<< "$OUTPUT"
grep -q '^symbol_group=BR$' <<< "$OUTPUT"
grep -q '^side=LONG$' <<< "$OUTPUT"
grep -q '^grid_rows=5$' <<< "$OUTPUT"
grep -q '^search_executed=1$' <<< "$OUTPUT"

grep -q \
'^GRID_RESULT rank=1 .*code=BRU6_LOCAL_S1.7_R1.8 .*state=BASELINE_SUPERIOR_GROSS_NEGATIVE$' \
<<< "$OUTPUT"

grep -q '^gross_positive_and_baseline_superior=0$' <<< "$OUTPUT"
grep -q '^target_edge_candidates=0$' <<< "$OUTPUT"

grep -q '^db_writes_performed=0$' <<< "$OUTPUT"
grep -q '^production_pipeline_changed=0$' <<< "$OUTPUT"
grep -q '^production_variant_family_changed=0$' <<< "$OUTPUT"
grep -q '^thresholds_changed=0$' <<< "$OUTPUT"
grep -q '^net_first_logic_changed=0$' <<< "$OUTPUT"
grep -q '^runtime_changed=0$' <<< "$OUTPUT"
grep -q '^execution_changed=0$' <<< "$OUTPUT"
grep -q '^orders_changed=0$' <<< "$OUTPUT"
grep -q '^fills_changed=0$' <<< "$OUTPUT"
grep -q '^micro_live_allowed=0$' <<< "$OUTPUT"

grep -q \
'^VERDICT=BRU6_CURRENT_CONTRACT_NEIGHBORHOOD_SEARCH_V1_READY$' \
<<< "$OUTPUT"

echo "VERDICT=TEST_BRU6_CURRENT_CONTRACT_NEIGHBORHOOD_SEARCH_V1_OK"
