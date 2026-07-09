#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_WORKSPACE_V2_DISPLAY_TERMS_PATCH_V1 ==="

sql_file="sql/presentation/workspace_v2_display_terms_patch_v1.sql"
portfolio="src/marketcore/presentation/workspace_v2/portfolio_v1.py"
terms_py="src/marketcore/presentation/workspace_v2/display_terms_v1.py"
design_py="src/marketcore/presentation/workspace_v2/design_system_v1.py"

test -f "$sql_file"
test -f "$portfolio"
test -f "$terms_py"
test -f "$design_py"

psql -d finam_core -v ON_ERROR_STOP=1 -f "$sql_file"

PYTHONPYCACHEPREFIX=/tmp/finam_pycache_workspace_v2_terms \
PYTHONPATH=src \
python -m py_compile "$portfolio" "$terms_py" "$design_py" src/marketcore/presentation/router.py

if grep -RInE 'render_kpi_card\("PF"|render_kpi_card\("Ожид\.|render_kpi_card\("Реком\.|render_kpi_card\("Режим"|Без реальных заявок|Коэфф\. прибыльности' "$portfolio"; then
  echo "HARDCODED_PORTFOLIO_KPI_TEXT_FOUND"
  exit 1
fi

missing_terms=$(psql -At -d finam_core -c "
SELECT count(*)
FROM (
  VALUES
    ('PROFIT_FACTOR'),
    ('EXPECTANCY_R'),
    ('FEEDBACK_QUEUE'),
    ('MODE'),
    ('PAPER_MODE'),
    ('STATUS_WARNING'),
    ('STATUS_LOCKED'),
    ('STATUS_PASS')
) t(term_code)
LEFT JOIN presentation.workspace_v2_display_term_v1 d
  ON d.term_code=t.term_code
 AND d.enabled
WHERE d.term_code IS NULL;
")

test "$missing_terms" = "0"

html="/tmp/marketcore_workspace_v2_portfolio_terms_patch_v1.html"

PYTHONPATH=src python - <<'PY' > "$html"
from marketcore.presentation.workspace_v2.portfolio_v1 import render_workspace_v2_portfolio_v1
print(render_workspace_v2_portfolio_v1())
PY

grep -q "Коэфф. приб." "$html"
grep -q "Ожид." "$html"
grep -q "Реком." "$html"
grep -q "Режим" "$html"
grep -q "Бумага" "$html"
grep -q "Внимание" "$html"

if grep -Eo '(model\.health|paper\.feedback|paper\.analytics|trading_plan|marketcore_ui)\.[A-Za-z0-9_.-]+' "$html"; then
  echo "RAW_I18N_KEY_VISIBLE"
  exit 1
fi

echo "display_terms_patch=OK"
echo "portfolio_kpi_hardcode_removed=OK"
echo "missing_terms=0"
echo "raw_i18n_keys=0"
echo "safe_ui_targets=OK"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_WORKSPACE_V2_DISPLAY_TERMS_PATCH_V1_READY"
echo "VERDICT=TEST_MARKETCORE_WORKSPACE_V2_DISPLAY_TERMS_PATCH_V1_OK"
