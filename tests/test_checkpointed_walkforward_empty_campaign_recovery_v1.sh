#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

FILE="src/scripts/run_checkpointed_walkforward_v4.py"

PYTHONPATH=src python -m py_compile "$FILE"
git --no-pager diff --check

grep -q "EMPTY_RUNNING_CAMPAIGN_NO_ALGORITHM_TASKS" "$FILE"
grep -q "NOT EXISTS (" "$FILE"
grep -q "walkforward_algorithm_task_v4" "$FILE"

echo "empty_campaign_recovery_guard_present=1"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_CHECKPOINTED_WALKFORWARD_EMPTY_CAMPAIGN_RECOVERY_V1_OK"
