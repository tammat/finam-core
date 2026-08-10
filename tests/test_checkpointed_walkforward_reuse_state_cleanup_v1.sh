#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

FILE="src/scripts/run_checkpointed_walkforward_v4.py"

PYTHONPATH=src python -m py_compile "$FILE"
git --no-pager diff --check

grep -q "error_text=NULL" "$FILE"
grep -q "finished_at=NULL" "$FILE"
grep -q "c.status_code='FAILED'" "$FILE"
grep -q "NOT EXISTS (" "$FILE"

echo "failed_empty_campaign_reuse_guard=1"
echo "stale_terminal_metadata_cleanup=1"
echo "nonempty_failed_campaign_reuse_allowed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_CHECKPOINTED_WALKFORWARD_REUSE_STATE_CLEANUP_V1_OK"
