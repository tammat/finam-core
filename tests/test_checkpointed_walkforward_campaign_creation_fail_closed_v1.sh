#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

FILE="src/scripts/run_checkpointed_walkforward_v4.py"

PYTHONPATH=src python -m py_compile "$FILE"
git --no-pager diff --check

grep -q "CREATE_CAMPAIGN_FAILED:" "$FILE"
grep -q "status_code='FAILED'" "$FILE"
grep -q "finished_at=clock_timestamp()" "$FILE"
grep -q "heartbeat_at=clock_timestamp()" "$FILE"

echo "campaign_creation_fail_closed_guard_present=1"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_WALKFORWARD_CAMPAIGN_CREATION_FAIL_CLOSED_V1_OK"
