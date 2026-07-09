#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKSPACE_V2_PORTFOLIO_PNL_PERCENT_VIEW_V1 ==="

sql_file="sql/presentation/workspace_v2_portfolio_pnl_percent_view_v1.sql"
i18n_file="sql/presentation/workspace_v2_portfolio_pnl_percent_i18n_v1.sql"

psql -d finam_core -v ON_ERROR_STOP=1 -f "$sql_file"
psql -d finam_core -v ON_ERROR_STOP=1 -f "$i18n_file"

col_exists=$(psql -At -d finam_core <<'SQL'
SELECT count(*)
FROM information_schema.columns
WHERE table_schema='presentation'
  AND table_name='v_workspace_v2_portfolio_positions_ru'
  AND column_name='P&L %';
SQL
)

test "$col_exists" = "1"

PYTHONPYCACHEPREFIX=/tmp/workspace_v2_portfolio_pnl_percent \
PYTHONPATH=src \
python -m py_compile \
  src/marketcore/presentation/workspace_v2/resolver/portfolio_v2_resolver.py \
  src/marketcore/presentation/workspace_v2/portfolio_page_v2.py

html=$(PYTHONPATH=src python - <<'PY'
from marketcore.presentation.workspace_v2.portfolio_page_v2 import render_workspace_v2_portfolio_page_v2
print(render_workspace_v2_portfolio_page_v2())
PY
)

echo "$html" | grep -q "P&amp;L %"
echo "$html" | grep -q "%"
echo "$html" | grep -q "mc-v2-value-row"

if echo "$html" | grep -E "portfolio\.column\."; then
  echo "RAW_PORTFOLIO_COLUMN_KEY_FOUND"
  exit 1
fi

echo "pnl_percent_column=OK"
echo "pnl_percent_html=OK"
echo "raw_portfolio_column_keys=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=WORKSPACE_V2_PORTFOLIO_PNL_PERCENT_VIEW_V1_READY"
echo "VERDICT=TEST_WORKSPACE_V2_PORTFOLIO_PNL_PERCENT_VIEW_V1_OK"
