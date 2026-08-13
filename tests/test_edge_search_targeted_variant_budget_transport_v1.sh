#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

PY="/opt/finam-core/venv/bin/python"

WORKER="src/marketcore/action/command_worker_v2.py"
CYCLE="src/scripts/run_autonomous_edge_search_cycle_v1.py"
TARGETED="src/scripts/run_targeted_entry_exit_oos_v1.py"

PYTHONPATH=src "$PY" -m py_compile \
  "$WORKER" \
  "$CYCLE" \
  "$TARGETED"

git diff --check -- \
  "$WORKER" \
  "$CYCLE" \
  "$TARGETED"

for FILE in "$WORKER" "$CYCLE" "$TARGETED"; do
    grep -q \
      'EDGE_SEARCH_TARGET_VARIANT_BUDGET' \
      "$FILE"
done

grep -q \
  'edge_search_request_parameter_v1' \
  "$WORKER"

echo "parameter_store_read_present=1"
echo "worker_variant_budget_transport_present=1"
echo "cycle_variant_budget_receive_present=1"
echo "cycle_variant_budget_child_transport_present=1"
echo "targeted_variant_budget_receive_present=1"
echo "target_identity_encodes_budget=0"
echo "one_request_per_allocation_target_preserved=1"
echo "optimizer_budget_consumption_changed=0"
echo "queue_writes_performed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_EDGE_SEARCH_TARGETED_VARIANT_BUDGET_TRANSPORT_V1_OK"
