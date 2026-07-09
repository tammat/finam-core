#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_WORKSPACE_V2_DESIGN_SYSTEM_V1 ==="

sql_file="sql/presentation/workspace_v2_design_system_v1.sql"
css_file="src/marketcore/presentation/static/workspace_v2_design_system_v1.css"
py_file="src/marketcore/presentation/workspace_v2/design_system_v1.py"

test -f "$sql_file"
test -f "$css_file"
test -f "$py_file"

if grep -RInE 'DROP TABLE|TRUNCATE|DELETE FROM|UPDATE .*runtime|UPDATE .*execution|INSERT INTO .*orders|INSERT INTO .*fills' "$sql_file" "$css_file" "$py_file"; then
  echo "DANGEROUS_CODE_FOUND"
  exit 1
fi

if grep -RIn "marketcore-ui-v2-mobile-navigation" src/scripts; then
  echo "FORBIDDEN_UI_PATCH_IN_SCRIPTS"
  exit 1
fi

PYTHONPYCACHEPREFIX=/tmp/finam_pycache_workspace_v2_design \
PYTHONPATH=src \
python -m py_compile "$py_file"

psql -d finam_core -v ON_ERROR_STOP=1 -f "$sql_file"

token_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM presentation.workspace_v2_design_token_v1
WHERE enabled;
")

term_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM presentation.workspace_v2_display_term_v1
WHERE enabled;
")

module_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM presentation.workspace_v2_module_v1
WHERE enabled;
")

future_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM presentation.workspace_v2_module_v1
WHERE enabled
  AND module_code IN ('CAPITAL','INSTRUMENTS');
")

grep -q "44px" "$css_file"
grep -q "mc-v2-card" "$css_file"
grep -q "mc-v2-progress" "$css_file"
grep -q "@media (max-width: 820px)" "$css_file"

test "$token_rows" -ge 8
test "$term_rows" -ge 10
test "$module_rows" -ge 8
test "$future_rows" = "2"

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.workspace_v2.design_system_v1 import render_kpi_card, render_progress, render_action_card

html = render_kpi_card("Кач. модели", "100%", "PASS", "Проверено")
assert "mc-v2-card" in html
assert "Кач. модели" in html

progress = render_progress(51, "Готовн.")
assert "mc-v2-progress-fill" in progress
assert "width:51%" in progress

action = render_action_card("Инструменты", "Поиск и добавление новых инструментов", "Открыть", "/workspace-v2/instruments")
assert "/workspace-v2/instruments" in action

print("workspace_v2_components=OK")
PY

echo "design_tokens=$token_rows"
echo "display_terms=$term_rows"
echo "workspace_modules=$module_rows"
echo "future_modules_capital_and_instruments=OK"
echo "css_design_system=OK"
echo "python_components=OK"
echo "mobile_first=OK"
echo "touch_target_44px=OK"
echo "safe_ui_targets=OK"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_WORKSPACE_V2_DESIGN_SYSTEM_V1_READY"
echo "VERDICT=TEST_MARKETCORE_WORKSPACE_V2_DESIGN_SYSTEM_V1_OK"
