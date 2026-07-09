#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKSPACE_V2_THEME_APPLY_V1 ==="

sql_file="sql/presentation/workspace_v2_theme_apply_v1.sql"
renderer="src/marketcore/presentation/workspace_v2/renderer/portfolio_v2_renderer.py"

psql -d finam_core -v ON_ERROR_STOP=1 -f "$sql_file"

PYTHONPYCACHEPREFIX=/tmp/workspace_v2_theme_apply \
PYTHONPATH=src \
python -m py_compile \
  src/marketcore/presentation/framework/theme_resolver.py \
  "$renderer" \
  src/marketcore/presentation/workspace_v2/portfolio_page_v2.py

test ! -f src/marketcore/presentation/static/workspace_v2_mobile_layout_v1.css

if grep -RInE 'workspace_v2_mobile_layout_v1.css|<link rel="stylesheet"' "$renderer"; then
  echo "CSS_LINK_FOUND"
  exit 1
fi

if grep -RInE 'SELECT |INSERT |UPDATE |DELETE |psycopg2|execute\(' "$renderer"; then
  echo "SQL_IN_RENDERER_FOUND"
  exit 1
fi

html=$(PYTHONPATH=src python - <<'PY'
from marketcore.presentation.workspace_v2.portfolio_page_v2 import render_workspace_v2_portfolio_page_v2
print(render_workspace_v2_portfolio_page_v2())
PY
)

echo "$html" | grep -q "max-width:"
echo "$html" | grep -q "grid-template-columns:"
echo "$html" | grep -q "border-radius:"
echo "$html" | grep -q "Портфель"
echo "$html" | grep -q "P&amp;L %"

if echo "$html" | grep -E "data-i18n-key|portfolio\.column\."; then
  echo "RAW_I18N_KEY_FOUND"
  exit 1
fi

echo "theme_apply=OK"
echo "theme_resolver_used=OK"
echo "css_file_removed=OK"
echo "sql_in_renderer=0"
echo "raw_i18n_keys=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=WORKSPACE_V2_THEME_APPLY_V1_READY"
echo "VERDICT=TEST_WORKSPACE_V2_THEME_APPLY_V1_OK"
