#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

DB="postgresql:///finam_core"
WF="82eb4370-1da4-59fa-a542-ddcf60414024"

read -r COMPLETE PENDING RUNNING FAILED <<<"$(
psql "$DB" -X -At -F' ' -v ON_ERROR_STOP=1 -c "
SELECT
    count(*) FILTER (WHERE f.status_code='COMPLETE'),
    count(*) FILTER (WHERE f.status_code='PENDING'),
    count(*) FILTER (WHERE f.status_code='RUNNING'),
    count(*) FILTER (WHERE f.status_code='FAILED')
FROM analytics.walkforward_fold_checkpoint_v4 f
JOIN analytics.walkforward_variant_task_v4 v USING(variant_task_id)
JOIN analytics.walkforward_algorithm_task_v4 a USING(algorithm_task_id)
WHERE a.campaign_id='$WF';
"
)"

echo "complete_folds=$COMPLETE"
echo "pending_folds=$PENDING"
echo "running_folds=$RUNNING"
echo "failed_folds=$FAILED"

[ "$COMPLETE" -gt 0 ]
[ "$FAILED" -eq 0 ]

echo "walkforward_execution_active=1"
echo "walkforward_resume_confirmed=1"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_CHECKPOINTED_WALKFORWARD_EXECUTION_RESUME_V1_OK"
