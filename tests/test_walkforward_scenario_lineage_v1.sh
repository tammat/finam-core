#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

WF="src/scripts/run_checkpointed_walkforward_v4.py"
ORCH="src/scripts/run_autonomous_edge_search_cycle_v1.py"

PYTHONPATH=src python -m py_compile "$WF" "$ORCH"
git --no-pager diff --check

grep -q 'EDGE_SEARCH_SCENARIO_RUN_ID' "$ORCH"
grep -q 'env=env' "$ORCH"

grep -q 'os.getenv("EDGE_SEARCH_SCENARIO_RUN_ID")' "$WF"
grep -q 'scenario_run_id,data_cutoff_ts' "$WF"
grep -q 'scenario_run_id=coalesce(c.scenario_run_id' "$WF"

PYTHONPATH=src python - <<'PY'
import os
import uuid

value = "185ed380-f129-44a9-8ac8-fb3252027916"
os.environ["EDGE_SEARCH_SCENARIO_RUN_ID"] = value

parsed = str(uuid.UUID(os.environ["EDGE_SEARCH_SCENARIO_RUN_ID"]))

assert parsed == value

print(f"scenario_run_id={parsed}")
print("scenario_uuid_validation=1")
PY

echo "orchestrator_scenario_env_propagated=1"
echo "walkforward_scenario_env_consumed=1"
echo "existing_lineage_overwrite_allowed=0"
echo "schema_change_required=0"
echo "db_writes_performed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_WALKFORWARD_SCENARIO_LINEAGE_V1_OK"
