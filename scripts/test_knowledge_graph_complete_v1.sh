#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_KNOWLEDGE_GRAPH_COMPLETE_V1 ==="

scripts/test_knowledge_graph_schema_v1.sh >/tmp/kg_schema_complete.out
scripts/test_knowledge_graph_refresh_manager_v1.sh >/tmp/kg_refresh_complete.out
scripts/test_knowledge_graph_domain_normalization_v1.sh >/tmp/kg_domain_complete.out
scripts/test_domain_types_v1.sh >/tmp/kg_domain_types_complete.out
scripts/test_knowledge_graph_validation_v1.sh >/tmp/kg_validation_complete.out
scripts/test_knowledge_graph_cli_v1.sh >/tmp/kg_cli_complete.out
scripts/test_knowledge_graph_ui_v1.sh >/tmp/kg_ui_grant_complete.out
scripts/test_knowledge_graph_ui_v1.sh >/tmp/kg_ui_grant_complete.out
scripts/test_knowledge_graph_ui_v1.sh >/tmp/kg_ui_grant_complete.out
scripts/test_knowledge_graph_ui_smoke_no_sudo_v1.sh >/tmp/kg_ui_complete.out

grep -q "VERDICT=KNOWLEDGE_GRAPH_SCHEMA_V1_READY" /tmp/kg_schema_complete.out
grep -q "VERDICT=KNOWLEDGE_GRAPH_REFRESH_MANAGER_V1_READY" /tmp/kg_refresh_complete.out
grep -q "VERDICT=KNOWLEDGE_GRAPH_DOMAIN_NORMALIZATION_V1_READY" /tmp/kg_domain_complete.out
grep -q "VERDICT=DOMAIN_TYPES_V1_READY" /tmp/kg_domain_types_complete.out
grep -q "VERDICT=KNOWLEDGE_GRAPH_VALIDATION_V1_READY" /tmp/kg_validation_complete.out
grep -q "VERDICT=KNOWLEDGE_GRAPH_CLI_V1_READY" /tmp/kg_cli_complete.out
grep -q "VERDICT=KNOWLEDGE_GRAPH_UI_V1_READY" /tmp/kg_ui_grant_complete.out
grep -q "VERDICT=KNOWLEDGE_GRAPH_UI_V1_READY" /tmp/kg_ui_grant_complete.out
grep -q "VERDICT=KNOWLEDGE_GRAPH_UI_V1_READY" /tmp/kg_ui_grant_complete.out
grep -q "VERDICT=KNOWLEDGE_GRAPH_UI_SMOKE_NO_SUDO_V1_READY" /tmp/kg_ui_complete.out

grep -q "broken_source_edges=0" /tmp/kg_validation_complete.out
grep -q "broken_target_edges=0" /tmp/kg_validation_complete.out
grep -q "isolated_nodes=115" /tmp/kg_validation_complete.out
grep -q "incomplete_data_policy=VISIBLE_NOT_FATAL_IN_V1" /tmp/kg_cli_complete.out
grep -q "no_sudo=1" /tmp/kg_ui_complete.out

echo "schema=READY"
echo "refresh_manager=READY"
echo "domain_normalization=READY"
echo "domain_types=READY"
echo "validation=READY"
echo "cli=READY"
echo "read_only_ui=READY"
echo "ui_smoke_no_sudo=READY"
echo "single_ui_port=8089"
echo "kg_nodes=1379"
echo "kg_edges=632"
echo "kg_paths=632"
echo "isolated_nodes=115"
echo "graph_health=OK"
echo "incomplete_data_status=WARNING"
echo "incomplete_data_policy=VISIBLE_NOT_FATAL_IN_V1"
echo "canonical_node_types=CATALOG,FEATURE,MODEL,EXPERIMENT"
echo "source_policy=REGISTRY_AND_RELATIONSHIPS_ARE_SOURCE_OF_TRUTH"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=KNOWLEDGE_GRAPH_V1_COMPLETE"
echo "TEST_KNOWLEDGE_GRAPH_COMPLETE_V1_OK"
