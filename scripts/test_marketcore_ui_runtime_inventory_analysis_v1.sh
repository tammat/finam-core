#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

echo "=== TEST_MARKETCORE_UI_RUNTIME_INVENTORY_ANALYSIS_V1 ==="

inventory_test="scripts/test_marketcore_ui_runtime_inventory_v1.sh"
analysis_script="src/scripts/presentation/analyze_ui_runtime_inventory_v1.py"
inventory_report="reports/marketcore_ui_runtime_inventory_v1.txt"
analysis_report="reports/marketcore_ui_runtime_inventory_analysis_v1.txt"

test -x "$inventory_test"
test -f "$analysis_script"

# Обеспечиваем наличие актуального исходного inventory.
"$inventory_test" >/tmp/marketcore_ui_runtime_inventory_v1.log

test -f "$inventory_report"

PYTHONPYCACHEPREFIX=/tmp/marketcore_ui_runtime_inventory_analysis_v1 \
PYTHONPATH=src \
python -m py_compile "$analysis_script"

if grep -nE \
  'send_order|place_order|cancel_order|execute_order|INSERT INTO|UPDATE |DELETE FROM|DROP TABLE|TRUNCATE' \
  "$analysis_script"
then
  echo "DANGEROUS_CODE_FOUND"
  exit 1
fi

PYTHONPATH=src \
python "$analysis_script" | tee "$analysis_report"

grep -q \
  "ui_runtime_status=RUNTIME_NOT_FOUND" \
  "$analysis_report"

grep -q \
  "render_tree_json_endpoints=READY" \
  "$analysis_report"

grep -q \
  "existing_design_system_css=AVAILABLE" \
  "$analysis_report"

grep -q \
  "selected_variant=C" \
  "$analysis_report"

grep -q \
  "decision=CREATE_UI_RUNTIME_CONTRACT_FIRST" \
  "$analysis_report"

grep -q \
  "NEXT_STEP" \
  "$analysis_report"

grep -q \
  "MARKETCORE_UI_RUNTIME_CONTRACT_V1" \
  "$analysis_report"

grep -q \
  "VERDICT=MARKETCORE_UI_RUNTIME_INVENTORY_ANALYSIS_V1_READY" \
  "$analysis_report"

echo "inventory_analysis=OK"
echo "selected_variant=C"
echo "ui_runtime_found=0"
echo "render_tree_endpoints_ready=1"
echo "design_system_css_available=1"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_MARKETCORE_UI_RUNTIME_INVENTORY_ANALYSIS_V1_OK"
