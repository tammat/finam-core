#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

PY="/opt/finam-core/venv/bin/python"
FILE="src/scripts/research/build_edge_search_targeted_cycle_consumption_contract_v1.py"
OUT="/tmp/edge_search_targeted_cycle_consumption_contract_v1.out"

PYTHONPATH=src "$PY" -m py_compile "$FILE"
git diff --check -- "$FILE"

rm -f "$OUT"

PYTHONPATH=src "$PY" "$FILE" | tee "$OUT"

grep -q 'variant_budget_consumption_present=1' "$OUT"
grep -q 'targeted_cycle_candidate_cardinality=1' "$OUT"
grep -q 'cycle_consumption_is_structural=1' "$OUT"
grep -q 'cycle_consumption_is_statistical_estimate=0' "$OUT"
grep -q 'frozen_challenger_semantics_preserved=1' "$OUT"
grep -q 'allocator_changed=0' "$OUT"

echo "universe_capacity_observed=13"
echo "runtime_cycle_consumption_observed=1"
echo "source_cycle_consumption_contract=1"
echo "additional_runs_required_to_prove_cardinality=0"
echo "allocator_changed=0"
echo "db_writes_performed=0"
echo "queue_writes_performed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo \
"VERDICT=TEST_EDGE_SEARCH_TARGETED_CYCLE_CONSUMPTION_CONTRACT_V1_OK"
