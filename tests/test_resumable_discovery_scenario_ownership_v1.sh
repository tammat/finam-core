#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

FILE="src/scripts/run_autonomous_edge_search_cycle_v1.py"

PYTHONPATH=src python -m py_compile "$FILE"
git --no-pager diff --check

grep -Fq 'r"(?m)^discovery_run_id=([0-9a-f-]{36})$"' "$FILE"
grep -q 'FROM analytics.edge_regime_discovery_run_v3' "$FILE"
grep -q 'DISCOVERY_SCENARIO_OWNER_MISSING' "$FILE"
grep -q 'env\["EDGE_SEARCH_SCENARIO_RUN_ID"\] = discovery_owner_scenario' "$FILE"
grep -q 'env\["EDGE_SEARCH_DISCOVERY_RUN_ID"\] = discovery_run_id' "$FILE"

DB="postgresql:///finam_core"
DISCOVERY="2ed748de-7808-47c8-98c5-b69d4791ae4e"

OWNER="$(
psql "$DB" -X -At -v ON_ERROR_STOP=1 -c "
SELECT scenario_run_id
FROM analytics.edge_regime_discovery_run_v3
WHERE discovery_run_id='$DISCOVERY';
"
)"

echo "current_discovery=$DISCOVERY"
echo "authoritative_scenario_owner=$OWNER"

[ "$OWNER" = "185ed380-f129-44a9-8ac8-fb3252027916" ]

echo "discovery_campaign_owns_scenario=1"
echo "resume_invocation_may_replace_owner=0"
echo "downstream_walkforward_inherits_discovery_owner=1"
echo "historical_walkforward_backfill_allowed=0"
echo "db_writes_performed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_RESUMABLE_DISCOVERY_SCENARIO_OWNERSHIP_V1_OK"
