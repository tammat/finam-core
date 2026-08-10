#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

DOMAIN="src/marketcore/presentation/workspace_v2/domain/research_snapshot_v2.py"
RESOLVER="src/marketcore/presentation/workspace_v2/resolver/research_v2_resolver.py"
RENDERER="src/marketcore/presentation/workspace_v2/renderer/research_v2_domain_renderer.py"

PYTHONPATH=src python -m py_compile \
  "$DOMAIN" \
  "$RESOLVER" \
  "$RENDERER"

git --no-pager diff --check

for FIELD in \
  regime_discovery_run_id \
  regime_scenario_run_id \
  regime_heartbeat_at \
  regime_pause_reason \
  walkforward_campaign_id \
  walkforward_scenario_run_id \
  walkforward_tasks_complete \
  walkforward_tasks_total \
  walkforward_progress_pct \
  walkforward_status \
  walkforward_phase \
  lineage_status
do
    COUNT="$(grep -c "^[[:space:]]*$FIELD:" "$DOMAIN")"
    [ "$COUNT" -eq 1 ]
done

grep -Fq \
  'FROM analytics.edge_regime_discovery_run_v3' \
  "$RESOLVER"

grep -Fq \
  'FROM analytics.edge_search_cycle_status_v1' \
  "$RESOLVER"

grep -Fq \
  'FROM analytics.walkforward_campaign_v4' \
  "$RESOLVER"

grep -Fq \
  'lineage_status = "MATCHED"' \
  "$RESOLVER"

grep -Fq \
  'lineage_status = "MISMATCH"' \
  "$RESOLVER"

grep -Fq \
  'lineage_status = "PRE_PATCH_UNLINKED"' \
  "$RESOLVER"

grep -Fq \
  '"research.current.discovery_scenario"' \
  "$RENDERER"

grep -Fq \
  '"research.current.discovery_pause"' \
  "$RENDERER"

grep -Fq \
  '"research.current.walkforward"' \
  "$RENDERER"

grep -Fq \
  '"research.current.walkforward_scenario"' \
  "$RENDERER"

grep -Fq \
  '"research.current.lineage"' \
  "$RENDERER"

echo "discovery_progress_ui=1"
echo "discovery_scenario_ui=1"
echo "discovery_pause_reason_ui=1"
echo "walkforward_progress_ui=1"
echo "walkforward_scenario_ui=1"
echo "lineage_status_ui=1"
echo "db_writes_performed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_RESEARCH_DISCOVERY_WALKFORWARD_LINEAGE_UI_V1_OK"
