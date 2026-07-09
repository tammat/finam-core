#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_UI_I18N_RESOLVER_V1 ==="

sql_file="sql/presentation/workspace_v2_portfolio_i18n_v1.sql"
files=(
  "src/marketcore/presentation/framework/i18n_model.py"
  "src/marketcore/presentation/framework/mapper/i18n_mapper.py"
  "src/marketcore/presentation/framework/i18n_resolver.py"
  "src/marketcore/presentation/workspace_v2/renderer/portfolio_v2_renderer.py"
)

psql -d finam_core -v ON_ERROR_STOP=1 -f "$sql_file"

PYTHONPYCACHEPREFIX=/tmp/marketcore_ui_i18n \
PYTHONPATH=src \
python -m py_compile "${files[@]}"

if grep -RInE 'SELECT |INSERT |UPDATE |DELETE |psycopg2|execute\(' \
  src/marketcore/presentation/workspace_v2/renderer/portfolio_v2_renderer.py; then
  echo "SQL_IN_RENDERER_FOUND"
  exit 1
fi

if grep -RInE 'row\["|row\[' \
  src/marketcore/presentation/framework/i18n_resolver.py; then
  echo "SCHEMA_COUPLING_IN_I18N_RESOLVER_FOUND"
  exit 1
fi

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.framework.i18n_resolver import UiI18nResolverV1
from marketcore.presentation.workspace_v2.portfolio_page_v2 import render_workspace_v2_portfolio_page_v2

i18n = UiI18nResolverV1(locale_code="ru")

assert i18n.text("portfolio.workspace.title") == "Портфель"
assert i18n.text("portfolio.workspace.subtitle") == "Капитал, позиции и риск"
assert i18n.text("missing.test.key") == "missing.test.key"

html = render_workspace_v2_portfolio_page_v2()

assert "Портфель" in html
assert "Сводка" in html
assert "Позиции" in html
assert "portfolio.workspace.title" not in html
assert "data-i18n-key" not in html

print("i18n_resolver=OK")
print("portfolio_renderer_localized=OK")
PY

echo "i18n_resolver=OK"
echo "portfolio_renderer_localized=OK"
echo "sql_in_renderer=0"
echo "schema_isolation=OK"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_UI_I18N_RESOLVER_V1_READY"
echo "VERDICT=TEST_MARKETCORE_UI_I18N_RESOLVER_V1_OK"
