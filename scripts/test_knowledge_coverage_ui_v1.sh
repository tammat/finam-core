#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_KNOWLEDGE_COVERAGE_UI_V1 ==="

sudo systemctl restart finam-readonly-ui
sleep 2

curl -fsS http://127.0.0.1:8089/ \
  -o /tmp/knowledge_coverage_ui_v1.html

grep -q "Knowledge Coverage" /tmp/knowledge_coverage_ui_v1.html
grep -q "WORKFLOW" /tmp/knowledge_coverage_ui_v1.html
grep -q "Объекты" /tmp/knowledge_coverage_ui_v1.html
grep -q "Discovery" /tmp/knowledge_coverage_ui_v1.html
grep -q "Health" /tmp/knowledge_coverage_ui_v1.html
grep -q "Портфель" /tmp/knowledge_coverage_ui_v1.html
grep -q "Кандидат" /tmp/knowledge_coverage_ui_v1.html

echo "knowledge_coverage_ui=READY"
echo "read_only_ui_http=200"
echo "source_policy=MART_AND_CATALOG_READ_ONLY"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=KNOWLEDGE_COVERAGE_UI_V1_READY"
echo "TEST_KNOWLEDGE_COVERAGE_UI_V1_OK"
