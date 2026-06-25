#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_GLOBAL_EDGE_SCORECARD_PERSISTENCE_PLAN_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_global_edge_scorecard_persistence_plan_v1.py

src/scripts/research/build_global_edge_scorecard_persistence_plan_v1.py \
  | tee /tmp/global_edge_scorecard_persistence_plan_v1.out

grep -q "GLOBAL_EDGE_SCORECARD_PERSISTENCE_PLAN_V1" /tmp/global_edge_scorecard_persistence_plan_v1.out
grep -q "global_edge_discovery_rows_are_stdout_only=1" /tmp/global_edge_scorecard_persistence_plan_v1.out
grep -q "table=research.analytics_global_edge_scorecard_v1" /tmp/global_edge_scorecard_persistence_plan_v1.out
grep -q "table=research.analytics_global_edge_scorecard_runs_v1" /tmp/global_edge_scorecard_persistence_plan_v1.out
grep -q "column=run_id" /tmp/global_edge_scorecard_persistence_plan_v1.out
grep -q "column=profit_factor" /tmp/global_edge_scorecard_persistence_plan_v1.out
grep -q "rule=scorecard_runs_are_append_only" /tmp/global_edge_scorecard_persistence_plan_v1.out
grep -q "next=GLOBAL_EDGE_SCORECARD_PERSISTENCE_SCHEMA_DRY_RUN_V1" /tmp/global_edge_scorecard_persistence_plan_v1.out
grep -q "VERDICT=GLOBAL_EDGE_SCORECARD_PERSISTENCE_PLAN_READY" /tmp/global_edge_scorecard_persistence_plan_v1.out

echo "TEST_GLOBAL_EDGE_SCORECARD_PERSISTENCE_PLAN_V1_OK"
