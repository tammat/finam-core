#!/usr/bin/env bash
set -euo pipefail

test -f scripts/create_today_pnl_views_v2.sql

grep -q "avg_short_price_before" scripts/create_today_pnl_views_v2.sql
grep -q "sell_amount_before / sell_qty_before - price" scripts/create_today_pnl_views_v2.sql
grep -q "price - buy_amount_before / buy_qty_before" scripts/create_today_pnl_views_v2.sql
grep -q "CREATE OR REPLACE VIEW v_today_trade_pnl_calc" scripts/create_today_pnl_views_v2.sql

echo "TODAY_PNL_VIEWS_V2_TEST_OK"
