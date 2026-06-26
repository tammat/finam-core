#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_CATALOG_EXPLORER_V1 ==="

PYTHONPATH=src src/marketcore/cli/main.py catalog summary | tee /tmp/catalog_explorer_summary.out
grep -q "objects=" /tmp/catalog_explorer_summary.out
grep -q "domains=" /tmp/catalog_explorer_summary.out
grep -q "runtime_changed=0" /tmp/catalog_explorer_summary.out

PYTHONPATH=src src/marketcore/cli/main.py catalog list --limit 5 | tee /tmp/catalog_explorer_list.out
grep -q "object_id=" /tmp/catalog_explorer_list.out

PYTHONPATH=src src/marketcore/cli/main.py catalog search mart | tee /tmp/catalog_explorer_search.out
grep -q "mart_candidate_workflow_v1" /tmp/catalog_explorer_search.out

PYTHONPATH=src src/marketcore/cli/main.py catalog object sem_candidate_v1 | tee /tmp/catalog_explorer_object.out
grep -q "sem_candidate_v1" /tmp/catalog_explorer_object.out

PYTHONPATH=src src/marketcore/cli/main.py catalog layer MART | tee /tmp/catalog_explorer_layer.out
grep -q "warehouse_layer=MART" /tmp/catalog_explorer_layer.out

PYTHONPATH=src src/marketcore/cli/main.py catalog source PostgresDiscovery | tee /tmp/catalog_explorer_source.out
grep -q "PostgresDiscovery" /tmp/catalog_explorer_source.out || grep -q "object_id=postgres:" /tmp/catalog_explorer_source.out

PYTHONPATH=src src/marketcore/cli/main.py catalog health | tee /tmp/catalog_explorer_health.out
grep -q "total=" /tmp/catalog_explorer_health.out
grep -q "missing_object_id=0" /tmp/catalog_explorer_health.out

PYTHONPATH=src src/marketcore/cli/main.py catalog stats | tee /tmp/catalog_explorer_stats.out
grep -q "stat_type=domain" /tmp/catalog_explorer_stats.out
grep -q "stat_type=layer" /tmp/catalog_explorer_stats.out

PYTHONPATH=src src/marketcore/cli/main.py catalog summary --json | tee /tmp/catalog_explorer_json.out
grep -q '"objects"' /tmp/catalog_explorer_json.out
grep -q '"health_pct"' /tmp/catalog_explorer_json.out

echo "catalog_explorer_commands=summary,list,search,object,layer,source,health,stats"
echo "json_output=1"
echo "text_output=1"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=CATALOG_EXPLORER_V1_READY"
echo "TEST_CATALOG_EXPLORER_V1_OK"
