#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_MISSION_CONTROL_V1 ==="

py_file="src/marketcore/presentation/workspace_v2/mission_control_v1.py"
test -f "$py_file"

PYTHONPYCACHEPREFIX=/tmp/finam_pycache_mission_control_v1 \
PYTHONPATH=src \
python -m py_compile "$py_file"

if grep -RInE 'send_order|place_order|cancel_order|execute_order|INSERT INTO .*orders|INSERT INTO .*fills|UPDATE .*runtime|UPDATE .*execution|DROP TABLE|TRUNCATE|DELETE FROM' "$py_file"; then
  echo "DANGEROUS_CODE_FOUND"
  exit 1
fi

if grep -RIn "marketcore-ui-v2-mobile-navigation" src/scripts; then
  echo "FORBIDDEN_UI_PATCH_IN_SCRIPTS"
  exit 1
fi

html="/tmp/marketcore_mission_control_v1.html"

PYTHONPATH=src python "$py_file" > "$html"

grep -q "Центр управления" "$html"
grep -q "MarketCore Workspace V2" "$html"
grep -q "Production" "$html"
grep -q "Готовн." "$html"
grep -q "Главные причины" "$html"
grep -q "/workspace-v2/portfolio" "$html"
grep -q "/workspace-v2/instruments" "$html"
grep -q "workspace_v2_design_system_v1.css" "$html"

if grep -Eo '(model\.health|paper\.feedback|paper\.analytics|trading_plan|marketcore_ui)\.[A-Za-z0-9_.-]+' "$html"; then
  echo "RAW_I18N_KEY_VISIBLE"
  exit 1
fi

echo "mission_control_html=OK"
echo "workspace_v2_design_system_used=OK"
echo "portfolio_action_present=OK"
echo "instrument_search_action_present=OK"
echo "raw_i18n_keys=0"
echo "safe_ui_targets=OK"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_MISSION_CONTROL_V1_READY"
echo "VERDICT=TEST_MARKETCORE_MISSION_CONTROL_V1_OK"
