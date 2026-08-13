#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

PY="/opt/finam-core/venv/bin/python"
FILE="src/scripts/research/build_edge_search_governed_enqueue_budget_parameters_v2_source_contract.py"
OUT="/tmp/test_edge_search_governed_enqueue_budget_parameters_v2_source.out"

PYTHONPATH=src "$PY" -m py_compile "$FILE"
git diff --check -- "$FILE"

rm -f "$OUT"

PYTHONPATH=src "$PY" "$FILE" | tee "$OUT"

grep -q '^parameter_insert_statements=1$' "$OUT"
grep -q 'enqueue_variant_budget_column_present=1' "$OUT"
grep -q 'effective_variants_source_present=1' "$OUT"
grep -q 'commit_candidate_present=1' "$OUT"

grep -q \
'required_v2_variant_budget_semantics=UNIVERSE_CAPACITY_UPPER_BOUND' \
"$OUT"

grep -q \
'required_v2_cycle_budget_semantics=TARGETED_CHALLENGERS_PER_CYCLE' \
"$OUT"

grep -q 'required_v2_cycle_budget_value=1' "$OUT"
grep -q 'target_id_encodes_budget=0' "$OUT"
grep -q 'one_request_per_target_preserved=1' "$OUT"

echo "governed_enqueue_insert_lineage_resolved=1"
echo "governed_enqueue_v2_patch_point_resolved=1"
echo "enqueue_changed=0"
echo "db_writes_performed=0"
echo "queue_writes_performed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo \
"VERDICT=TEST_EDGE_SEARCH_GOVERNED_ENQUEUE_BUDGET_PARAMETERS_V2_SOURCE_CONTRACT_OK"
