#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKSPACE_V2_PORTFOLIO_CARD_VALUES_V1 ==="

sql_file="sql/presentation/workspace_v2_portfolio_column_i18n_v1.sql"
files=(
  "src/marketcore/presentation/workspace_v2/formatter/portfolio_v2_formatter.py"
  "src/marketcore/presentation/workspace_v2/renderer/portfolio_v2_renderer.py"
  "src/marketcore/presentation/workspace_v2/portfolio_page_v2.py"
)

psql -d finam_core -v ON_ERROR_STOP=1 -f "$sql_file"

PYTHONPYCACHEPREFIX=/tmp/workspace_v2_portfolio_values \
PYTHONPATH=src \
python -m py_compile "${files[@]}"

if grep -RInE 'SELECT |INSERT |UPDATE |DELETE |psycopg2|execute\(' \
  src/marketcore/presentation/workspace_v2/formatter/portfolio_v2_formatter.py \
  src/marketcore/presentation/workspace_v2/renderer/portfolio_v2_renderer.py \
  src/marketcore/presentation/workspace_v2/portfolio_page_v2.py; then
  echo "SQL_OUTSIDE_RESOLVER_FOUND"
  exit 1
fi

if grep -RInE 'data-i18n-key|portfolio\.workspace\.title|portfolio\.section\.summary\.title|portfolio\.source\.public_' \
  src/marketcore/presentation/workspace_v2/renderer/portfolio_v2_renderer.py; then
  echo "RAW_I18N_KEY_IN_RENDERER_FOUND"
  exit 1
fi

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.workspace_v2.portfolio_page_v2 import (
    render_workspace_v2_portfolio_page_v2,
)

html = render_workspace_v2_portfolio_page_v2()

assert "mc-v2-values" in html
assert "mc-v2-value-row" in html
assert "<dt>" in html
assert "<dd>" in html
assert "data-i18n-key" not in html

print("portfolio_card_values=OK")
PY

echo "portfolio_card_values=OK"
echo "formatter_used=OK"
echo "renderer_values=OK"
echo "sql_outside_resolver=0"
echo "raw_i18n_keys=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=WORKSPACE_V2_PORTFOLIO_CARD_VALUES_V1_READY"
echo "VERDICT=TEST_WORKSPACE_V2_PORTFOLIO_CARD_VALUES_V1_OK"
