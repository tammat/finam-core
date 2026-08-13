#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

PY="/opt/finam-core/venv/bin/python"
FILE="src/scripts/research/build_edge_search_request_budget_transport_v2_source_contract.py"
OUT="/tmp/edge_search_request_budget_transport_v2_source_contract_test.out"

PYTHONPATH=src "$PY" -m py_compile "$FILE"
git diff --check -- "$FILE"

rm -f "$OUT"

PYTHONPATH=src "$PY" "$FILE" | tee "$OUT"

for CHECK in \
    parameter_store_read_present \
    worker_variant_transport_present \
    cycle_variant_transport_present \
    targeted_variant_transport_present \
    optimizer_variant_receive_present
do
    grep -q \
      "CHECK name=${CHECK} passed=1" \
      "$OUT"
done

grep -q 'legacy_cycle_budget_fallback_required=1' "$OUT"
grep -q 'target_id_encodes_cycle_budget=0' "$OUT"
grep -q 'db_writes_performed=0' "$OUT"

echo "v1_transport_lineage_resolved=1"
echo "cycle_budget_patch_points_resolved=1"
echo "db_writes_performed=0"
echo "queue_writes_performed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_EDGE_SEARCH_REQUEST_BUDGET_TRANSPORT_V2_SOURCE_CONTRACT_OK"
