#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

echo "=== TEST_MARKETCORE_UI_RUNTIME_INVENTORY_V1 ==="

inventory_script="src/scripts/presentation/ui_runtime_inventory_v1.py"
report="reports/marketcore_ui_runtime_inventory_v1.txt"

test -f "$inventory_script"

PYTHONPYCACHEPREFIX=/tmp/marketcore_ui_runtime_inventory_v1 \
PYTHONPATH=src \
python -m py_compile "$inventory_script"

if grep -nE \
  'send_order|place_order|cancel_order|execute_order|INSERT INTO|UPDATE |DELETE FROM|DROP TABLE|TRUNCATE' \
  "$inventory_script"
then
  echo "DANGEROUS_CODE_FOUND"
  exit 1
fi

PYTHONPATH=src \
python "$inventory_script" | tee "$report"

grep -q \
  "VERDICT=MARKETCORE_UI_RUNTIME_INVENTORY_V1_READY" \
  "$report"

grep -q "JAVASCRIPT_TYPESCRIPT_FILES" "$report"
grep -q "CSS_FILES" "$report"
grep -q "HTML_TEMPLATE_FILES" "$report"
grep -q "UI_RUNTIME_MARKERS" "$report"
grep -q "STATIC_DELIVERY_MARKERS" "$report"
grep -q "RENDER_TREE_ENDPOINT_REFERENCES" "$report"
grep -q "UI_RUNTIME_CANDIDATE_FILES" "$report"

echo "inventory_report=$report"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_MARKETCORE_UI_RUNTIME_INVENTORY_V1_OK"
