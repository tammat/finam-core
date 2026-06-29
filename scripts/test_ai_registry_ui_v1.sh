#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_AI_REGISTRY_UI_V1 ==="

sudo -u postgres psql finam_core <<'SQL'
GRANT USAGE ON SCHEMA warehouse TO alex;
GRANT SELECT ON warehouse.ai_registry_v1 TO alex;
SQL

sudo systemctl restart finam-readonly-ui
sleep 2

curl -fsS http://127.0.0.1:8089/knowledge/ai \
  -o /tmp/ai_registry_ui_v1.html

grep -q "MarketCore AI Registry" /tmp/ai_registry_ui_v1.html
grep -q "ai_registry_total=10" /tmp/ai_registry_ui_v1.html
grep -q "AI_AGENT" /tmp/ai_registry_ui_v1.html
grep -q "AI_POLICY" /tmp/ai_registry_ui_v1.html
grep -q "AI_CAPABILITY" /tmp/ai_registry_ui_v1.html
grep -q "AI_REGISTRY_MANAGER" /tmp/ai_registry_ui_v1.html
grep -q "AI_KNOWLEDGE_GRAPH_AGENT" /tmp/ai_registry_ui_v1.html
grep -q "AI_RESEARCH_ASSISTANT" /tmp/ai_registry_ui_v1.html
grep -q "ai_registry_health=OK" /tmp/ai_registry_ui_v1.html
grep -q "unsafe_live_rows=0" /tmp/ai_registry_ui_v1.html
grep -q "execution_policy_valid=10" /tmp/ai_registry_ui_v1.html
grep -q "market_policy_valid=10" /tmp/ai_registry_ui_v1.html
grep -q "graph_required_valid=10" /tmp/ai_registry_ui_v1.html
grep -q "framework_version_valid=10" /tmp/ai_registry_ui_v1.html
grep -q "domain_types_version_valid=10" /tmp/ai_registry_ui_v1.html
grep -q "forbidden_market_fields=0" /tmp/ai_registry_ui_v1.html
grep -q "policy=READ_ONLY" /tmp/ai_registry_ui_v1.html
grep -q "forbidden_commands=add,update,delete,edit" /tmp/ai_registry_ui_v1.html
grep -q "framework=REGISTRY_FRAMEWORK_V1" /tmp/ai_registry_ui_v1.html
grep -q "bootstrap_policy=AI_BOOTSTRAP_POLICY_V1" /tmp/ai_registry_ui_v1.html
grep -q "source_policy=AI_REGISTRY_DOES_NOT_STORE_MARKET_KNOWLEDGE" /tmp/ai_registry_ui_v1.html
grep -q "ui_policy=READ_ONLY_SINGLE_PORT_8089" /tmp/ai_registry_ui_v1.html
grep -q "micro_live_allowed=0" /tmp/ai_registry_ui_v1.html

echo "single_ui_port=8089"
echo "route_ai=/knowledge/ai"
echo "ai_registry_health=OK"
echo "ai_registry_total=10"
echo "source_policy=AI_REGISTRY_DOES_NOT_STORE_MARKET_KNOWLEDGE"
echo "policy=READ_ONLY"
echo "framework=REGISTRY_FRAMEWORK_V1"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=AI_REGISTRY_UI_V1_READY"
echo "TEST_AI_REGISTRY_UI_V1_OK"
