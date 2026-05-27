#!/usr/bin/env bash
set -euo pipefail

test -f scripts/create_today_pnl_views_from_intraday.sql

grep -q "FROM analytics_intraday_pnl" scripts/create_today_pnl_views_from_intraday.sql
grep -q "CREATE OR REPLACE VIEW v_today_trade_pnl_calc" scripts/create_today_pnl_views_from_intraday.sql
grep -q "CREATE OR REPLACE VIEW v_today_trades_ru" scripts/create_today_pnl_views_from_intraday.sql
grep -q "CREATE OR REPLACE VIEW v_today_pnl_summary_ru" scripts/create_today_pnl_views_from_intraday.sql
grep -q "position_qty_after" scripts/create_today_pnl_views_from_intraday.sql

echo "TODAY_PNL_VIEWS_FROM_INTRADAY_TEST_OK"
