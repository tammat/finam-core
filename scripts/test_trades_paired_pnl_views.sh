#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

test -f sql/20260511_trades_paired_pnl_views.sql

grep -q "v_trades_pnl_paired_ui" sql/20260511_trades_paired_pnl_views.sql
grep -q "v_trades_pnl_paired_grafana" sql/20260511_trades_paired_pnl_views.sql
grep -q "ROW_NUMBER() OVER" sql/20260511_trades_paired_pnl_views.sql
grep -q "Realized P&L" sql/20260511_trades_paired_pnl_views.sql
grep -q "DD-MM-YYYY HH24:MI" sql/20260511_trades_paired_pnl_views.sql

echo "TRADES_PAIRED_PNL_VIEWS_TEST_OK"
