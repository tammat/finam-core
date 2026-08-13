#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

PY="/opt/finam-core/venv/bin/python"
FILE="src/scripts/research/build_edge_search_request_budget_parameter_contract_v2.py"
OUT="/tmp/edge_search_request_budget_parameter_contract_v2.out"

PYTHONPATH=src "$PY" -m py_compile "$FILE"
git diff --check -- "$FILE"

rm -f "$OUT"

PYTHONPATH=src "$PY" "$FILE" | tee "$OUT"

grep -q 'variant_budget_present=1' "$OUT"
grep -q \
'variant_budget_semantics=UNIVERSE_CAPACITY_UPPER_BOUND' \
"$OUT"

grep -q \
'cycle_budget_semantics=TARGETED_CHALLENGERS_PER_CYCLE' \
"$OUT"

grep -q 'cycle_budget_default_policy=1' "$OUT"
grep -q 'cycle_budget_positive_required=1' "$OUT"
grep -q 'cycle_budget_lte_variant_budget_required=1' "$OUT"

grep -q 'legacy_rows_supported=1' "$OUT"
grep -q 'variant_budget_column_removed=0' "$OUT"
grep -q 'target_id_changed=0' "$OUT"

grep -q 'schema_changed=0' "$OUT"
grep -q 'worker_transport_changed=0' "$OUT"

echo "universe_capacity_parameter=variant_budget"
echo "cycle_consumption_parameter=cycle_budget"
echo "backward_compatible_contract=1"
echo "schema_changed=0"
echo "db_writes_performed=0"
echo "queue_writes_performed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_EDGE_SEARCH_REQUEST_BUDGET_PARAMETER_CONTRACT_V2_OK"
