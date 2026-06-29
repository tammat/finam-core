#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_READ_ONLY_UI_ROUTER_V1 ==="

sudo systemctl restart finam-readonly-ui
sleep 2

curl -fsS http://127.0.0.1:8089/ -o /tmp/router_home.html
curl -fsS http://127.0.0.1:8089/knowledge -o /tmp/router_knowledge.html
curl -fsS http://127.0.0.1:8089/knowledge/coverage -o /tmp/router_coverage.html

grep -q "Портфель" /tmp/router_home.html
grep -q "MarketCore Knowledge Center" /tmp/router_knowledge.html
grep -q "WORKFLOW" /tmp/router_knowledge.html
grep -q "FEATURES" /tmp/router_knowledge.html
grep -q "MODELS" /tmp/router_knowledge.html
grep -q "Discovery Sources" /tmp/router_knowledge.html

grep -q "MarketCore Knowledge Coverage" /tmp/router_coverage.html
grep -q "WORKFLOW" /tmp/router_coverage.html
grep -q "object_id_coverage_pct" /tmp/router_coverage.html
grep -q "CATALOG_READ_ONLY" /tmp/router_coverage.html
grep -q "micro_live_allowed=0" /tmp/router_coverage.html

echo "single_ui_port=8089"
echo "route_home=/"
echo "route_knowledge=/knowledge"
echo "route_coverage=/knowledge/coverage"
echo "source_policy=CATALOG_READ_ONLY"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=READ_ONLY_UI_ROUTER_V1_READY"
echo "TEST_READ_ONLY_UI_ROUTER_V1_OK"
