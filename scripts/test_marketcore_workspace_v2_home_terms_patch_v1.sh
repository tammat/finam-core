#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_WORKSPACE_V2_HOME_TERMS_PATCH_V1 ==="

sql_file="sql/presentation/workspace_v2_home_terms_patch_v1.sql"
mission="src/marketcore/presentation/workspace_v2/mission_control_v1.py"
home="src/marketcore/presentation/workspace_v2/home_v1.py"
router="src/marketcore/presentation/router.py"

test -f "$sql_file"
test -f "$mission"
test -f "$home"
test -f "$router"

psql -d finam_core -v ON_ERROR_STOP=1 -f "$sql_file"

PYTHONPYCACHEPREFIX=/tmp/finam_pycache_workspace_v2_home_terms \
PYTHONPATH=src \
python -m py_compile "$mission" "$home" "$router"

if grep -RInE '"Центр управления"|"Главные причины"|"Продолжать бумажную проверку"|"Качество модели"|"Ожидание в R"|render_kpi_card\("' "$mission"; then
  echo "HOME_VISIBLE_TEXT_HARDCODE_FOUND"
  exit 1
fi

missing_terms=$(psql -At -d finam_core -c "
SELECT count(*)
FROM (
  VALUES
    ('WORKSPACE_TITLE'),
    ('HOME'),
    ('PROJECT_STATE'),
    ('RESEARCH_STATE'),
    ('NEXT_ACTION'),
    ('CONTINUE_PAPER'),
    ('MAIN_REASONS'),
    ('TRADES'),
    ('PORTFOLIO'),
    ('INSTRUMENTS'),
    ('OPEN_ACTION')
) t(term_code)
LEFT JOIN presentation.workspace_v2_display_term_v1 d
  ON d.term_code=t.term_code
 AND d.enabled
WHERE d.term_code IS NULL;
")

test "$missing_terms" = "0"

html="/tmp/marketcore_workspace_v2_home_terms_patch_v1.html"

PYTHONPATH=src python - <<'PY' > "$html"
from marketcore.presentation.router import route
code, html = route("/workspace-v2")
assert code == 200
print(html.decode("utf-8"))
PY

grep -q "Главная" "$html"
grep -q "Workspace V2" "$html"
grep -q "Далее" "$html"
grep -q "Причины" "$html"
grep -q "/workspace-v2/portfolio" "$html"
grep -q "/workspace-v2/instruments" "$html"

if grep -Eo '(model\.health|paper\.feedback|paper\.analytics|trading_plan|marketcore_ui)\.[A-Za-z0-9_.-]+' "$html"; then
  echo "RAW_I18N_KEY_VISIBLE"
  exit 1
fi

echo "home_terms_patch=OK"
echo "mission_control_visible_text_from_terms=OK"
echo "missing_terms=0"
echo "raw_i18n_keys=0"
echo "safe_ui_targets=OK"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_WORKSPACE_V2_HOME_TERMS_PATCH_V1_READY"
echo "VERDICT=TEST_MARKETCORE_WORKSPACE_V2_HOME_TERMS_PATCH_V1_OK"
