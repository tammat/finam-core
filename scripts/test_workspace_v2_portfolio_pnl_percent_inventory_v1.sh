#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKSPACE_V2_PORTFOLIO_PNL_PERCENT_INVENTORY_V1 ==="

psql -d finam_core -P pager=off <<'SQL'
SELECT
  table_name,
  ordinal_position,
  column_name,
  data_type
FROM information_schema.columns
WHERE table_schema='public'
  AND table_name IN (
    'v_real_portfolio_summary_ru',
    'v_real_portfolio_positions_ru',
    'v_positions_dashboard_ru',
    'v_portfolio_visualization_ru'
  )
ORDER BY table_name, ordinal_position;
SQL

echo "VERDICT=WORKSPACE_V2_PORTFOLIO_PNL_PERCENT_INVENTORY_V1_READY"
echo "VERDICT=TEST_WORKSPACE_V2_PORTFOLIO_PNL_PERCENT_INVENTORY_V1_OK"
