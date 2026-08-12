#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

PY="/opt/finam-core/venv/bin/python"
SCRIPT="src/scripts/research/build_global_edge_physical_contract_frontier_v1.py"

echo "=== TEST GLOBAL EDGE PHYSICAL CONTRACT FRONTIER V1 ==="

PYTHONPATH=src "$PY" -m py_compile "$SCRIPT"

OUTPUT="$(
    PYTHONPATH=src "$PY" "$SCRIPT"
)"

printf '%s\n' "$OUTPUT"

grep -q '^PHYSICAL_FRONTIER_ROW ' <<< "$OUTPUT"

grep -q 'physical_symbol=BRQ6@RTSX ' <<< "$OUTPUT"
grep -q 'physical_symbol=BRU6@RTSX ' <<< "$OUTPUT"

grep -q '^brq6_present=1$' <<< "$OUTPUT"
grep -q '^bru6_present=1$' <<< "$OUTPUT"

grep -q '^physical_contract_identity_used=1$' <<< "$OUTPUT"
grep -q '^contract_mixing_allowed=0$' <<< "$OUTPUT"
grep -q '^physical_contract_segmentation_materialized=1$' <<< "$OUTPUT"

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
'^VERDICT=GLOBAL_EDGE_PHYSICAL_CONTRACT_FRONTIER_V1_READY$' \
<<< "$OUTPUT"

echo "VERDICT=TEST_GLOBAL_EDGE_PHYSICAL_CONTRACT_FRONTIER_V1_OK"
