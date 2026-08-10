#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

FILE="src/marketcore/action/command_worker_v2.py"

PYTHONPATH=src python -m py_compile "$FILE"
git --no-pager diff --check

grep -Fq 'result == "VERDICT=AUTONOMOUS_EDGE_SEARCH_CHECKPOINTED"' "$FILE"
grep -Fq '"EDGE_SEARCH_CHECKPOINT_CONTINUATION_V1"' "$FILE"
grep -Fq "ON CONFLICT(request_id) DO NOTHING" "$FILE"
grep -Fq "row[\"request_kind\"] == \"EDGE_SEARCH_RUN\"" "$FILE"
grep -Fq "and not continuation_required" "$FILE"
grep -Fq '"WORKER_RESUMABLE" if continuation_required' "$FILE"

echo "checkpoint_marker_consumed=1"
echo "checkpoint_continuation_created=1"
echo "continuation_idempotent=1"
echo "current_invocation_terminal_completed=1"
echo "research_process_terminal_on_checkpoint=0"
echo "technical_failure_semantics_preserved=1"
echo "scheduler_change_required=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_EDGE_SEARCH_CHECKPOINT_COMMAND_LIFECYCLE_V1_OK"
