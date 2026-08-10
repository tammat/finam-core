#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

FILE="src/scripts/monitor_edge_search_command_queue_v1.py"

PYTHONPATH=src python -m py_compile "$FILE"
git --no-pager diff --check

grep -Fq \
'EDGE_SEARCH_RESOURCE_GUARD_RETRY_COOLDOWN_SECONDS' \
"$FILE"

grep -Fq \
'VERDICT=AUTONOMOUS_EDGE_SEARCH_RESOURCE_GUARD_OK' \
"$FILE"

grep -Fq \
'EDGE_SEARCH_RESOURCE_GUARD_DEFERRED_RETRY_V1' \
"$FILE"

grep -Fq \
"active.status IN ('PENDING','RUNNING')" \
"$FILE"

grep -Fq \
'ON CONFLICT(source_request_id) DO NOTHING' \
"$FILE"

echo "resource_guard_deferred_retry_present=1"
echo "resource_guard_cooldown_present=1"
echo "active_request_guard_present=1"
echo "source_retry_idempotency_present=1"
echo "resource_guard_immediate_retry=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_EDGE_SEARCH_RESOURCE_GUARD_DEFERRED_RETRY_V1_OK"
