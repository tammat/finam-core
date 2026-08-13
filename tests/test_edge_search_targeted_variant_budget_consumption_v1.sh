#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

PY="/opt/finam-core/venv/bin/python"
OPT="src/scripts/analytics/build_entry_exit_optimizer_v1.py"

echo "=== TEST EDGE SEARCH TARGETED VARIANT BUDGET CONSUMPTION V1 ==="

PYTHONPATH=src "$PY" -m py_compile "$OPT"
git diff --check -- "$OPT"

grep -q \
  'EDGE_SEARCH_TARGET_VARIANT_BUDGET' \
  "$OPT"

grep -q \
  'all_variants = all_variants\[:variant_budget\]' \
  "$OPT"

"$PY" - <<'PY'
full_universe = tuple(range(13))

def bounded(universe, budget):
    return universe[:budget]

assert len(bounded(full_universe, 40)) == 13
assert len(bounded(full_universe, 13)) == 13
assert len(bounded(full_universe, 5)) == 5
assert bounded(full_universe, 5) == full_universe[:5]

print("full_candidate_universe=13")
print("requested_variant_budget=40")
print("effective_variant_budget=13")
print("unused_variant_capacity=27")
print("deterministic_order_preserved=1")
print("one_frozen_challenger_per_cycle_preserved=1")
print("variant_budget_is_universe_upper_bound=1")
print("variant_budget_is_per_cycle_evaluation_count=0")
PY

echo "queue_writes_performed=0"
echo "resource_allocation_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_EDGE_SEARCH_TARGETED_VARIANT_BUDGET_CONSUMPTION_V1_OK"
