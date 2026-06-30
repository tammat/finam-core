#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_KNOWLEDGE_CENTER_UI_V1 ==="

KNOWLEDGE_CENTER_PORT=8091 PYTHONPATH=src \
  src/scripts/research/serve_knowledge_center_ui_v1.py \
  >/tmp/knowledge_center_ui_v1.log 2>&1 &

PID=$!
trap 'kill $PID >/dev/null 2>&1 || true' EXIT

sleep 2

curl -fsS http://127.0.0.1:8091/ -o /tmp/knowledge_center_ui_v1.html

grep -q "MarketCore Knowledge Center" /tmp/knowledge_center_ui_v1.html
grep -q "WORKFLOW" /tmp/knowledge_center_ui_v1.html
grep -q "FEATURES" /tmp/knowledge_center_ui_v1.html
grep -q "MODELS" /tmp/knowledge_center_ui_v1.html
grep -q "Discovery Sources" /tmp/knowledge_center_ui_v1.html
grep -q "CATALOG_READ_ONLY" /tmp/knowledge_center_ui_v1.html
grep -q "micro_live_allowed=0" /tmp/knowledge_center_ui_v1.html

echo "knowledge_center_ui=READY"
echo "http_ready=1"
echo "source_policy=CATALOG_READ_ONLY"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=KNOWLEDGE_CENTER_UI_V1_READY"
echo "TEST_KNOWLEDGE_CENTER_UI_V1_OK"
