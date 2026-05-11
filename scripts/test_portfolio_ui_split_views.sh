#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

test -f sql/20260511_portfolio_ui_split_views.sql

grep -q "v_real_portfolio_positions_ui" sql/20260511_portfolio_ui_split_views.sql
grep -q "v_real_portfolio_pnl_ui" sql/20260511_portfolio_ui_split_views.sql
grep -q "DROP VIEW IF EXISTS v_real_portfolio_positions_ui" sql/20260511_portfolio_ui_split_views.sql
grep -q "DROP VIEW IF EXISTS v_real_portfolio_pnl_ui" sql/20260511_portfolio_ui_split_views.sql

! grep -q "order_id" sql/20260511_portfolio_ui_split_views.sql
! grep -q "client_order_id" sql/20260511_portfolio_ui_split_views.sql
! grep -q "orders_projection" sql/20260511_portfolio_ui_split_views.sql
! grep -q "dlq_events" sql/20260511_portfolio_ui_split_views.sql

echo "PORTFOLIO_UI_SPLIT_VIEWS_TEST_OK"
