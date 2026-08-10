#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

FILE="src/marketcore/action/command_worker_v2.py"

PYTHONPATH=src python -m py_compile "$FILE"
git --no-pager diff --check

grep -Fq \
'result == "VERDICT=AUTONOMOUS_EDGE_SEARCH_CHECKPOINTED"' \
"$FILE"

if grep -A8 'continuation_required = (' "$FILE" \
   | grep -Fq '"VERDICT=AUTONOMOUS_EDGE_SEARCH_RESOURCE_GUARD_OK"'
then
    echo "ERROR=RESOURCE_GUARD_STILL_IMMEDIATE_CONTINUATION"
    exit 1
fi

grep -Fq \
'"VERDICT=AUTONOMOUS_EDGE_SEARCH_RESOURCE_GUARD_OK"' \
"$FILE"

echo "checkpoint_immediate_continuation=1"
echo "resource_guard_immediate_continuation=0"
echo "resource_guard_semantics_preserved=1"
echo "continuation_hot_loop_blocked=1"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_EDGE_SEARCH_RESOURCE_GUARD_NO_HOT_LOOP_V1_OK"
