#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

echo "=== TEST_MARKETCORE_RENDER_TREE_DOMAIN_INVENTORY_V1 ==="

py_file="src/scripts/presentation/render_tree_domain_inventory_v1.py"
report="reports/marketcore_render_tree_domain_inventory_v1.txt"

test -f "$py_file"

PYTHONPYCACHEPREFIX=/tmp/marketcore_render_tree_domain_inventory_v1 \
PYTHONPATH=src \
python -m py_compile "$py_file"

if grep -RInE \
  'send_order|place_order|cancel_order|execute_order|INSERT INTO|UPDATE |DELETE FROM|DROP TABLE|TRUNCATE' \
  "$py_file"
then
    echo "DANGEROUS_CODE_FOUND"
    exit 1
fi

PYTHONPATH=src python "$py_file" | tee "$report"

grep -q \
  "VERDICT=MARKETCORE_RENDER_TREE_DOMAIN_INVENTORY_V1_READY" \
  "$report"

grep -q "CURRENT_NODE_TYPES" "$report"
grep -q "PLATFORM_NODE_TYPE_USAGE" "$report"
grep -q "LEGACY_RENDER_REFERENCES" "$report"
grep -q "PLATFORM_TERMS_INSIDE_RENDER_TREE" "$report"

echo "inventory_report=$report"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_MARKETCORE_RENDER_TREE_DOMAIN_INVENTORY_V1_OK"
