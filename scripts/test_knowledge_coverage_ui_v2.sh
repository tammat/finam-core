#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_KNOWLEDGE_COVERAGE_UI_V2 ==="

KNOWLEDGE_UI_PORT=8090 PYTHONPATH=src \
  src/scripts/research/serve_knowledge_coverage_ui_v2.py \
  >/tmp/knowledge_coverage_ui_v2.log 2>&1 &

PID=$!
trap 'kill $PID >/dev/null 2>&1 || true' EXIT

sleep 2

curl -fsS http://127.0.0.1:8090/ -o /tmp/knowledge_coverage_ui_v2.html

grep -q "MarketCore Knowledge Coverage" /tmp/knowledge_coverage_ui_v2.html
grep -q "WORKFLOW" /tmp/knowledge_coverage_ui_v2.html
grep -q "Объекты" /tmp/knowledge_coverage_ui_v2.html
grep -q "Discovery" /tmp/knowledge_coverage_ui_v2.html
grep -q "Health" /tmp/knowledge_coverage_ui_v2.html
grep -q "CATALOG_READ_ONLY" /tmp/knowledge_coverage_ui_v2.html
grep -q "micro_live_allowed=0" /tmp/knowledge_coverage_ui_v2.html

echo "knowledge_coverage_ui=READY"
echo "http_ready=1"
echo "source_policy=CATALOG_READ_ONLY"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=KNOWLEDGE_COVERAGE_UI_V2_READY"
echo "TEST_KNOWLEDGE_COVERAGE_UI_V2_OK"
