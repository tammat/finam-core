#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

test -f sql/20260511_trades_equity_curve_views.sql

grep -q "v_trades_equity_curve_ui" sql/20260511_trades_equity_curve_views.sql
grep -q "v_trades_equity_curve_grafana" sql/20260511_trades_equity_curve_views.sql
grep -q "SUM(\"Realized P&L\") OVER" sql/20260511_trades_equity_curve_views.sql
grep -q "Equity P&L" sql/20260511_trades_equity_curve_views.sql
grep -q "ts AS time" sql/20260511_trades_equity_curve_views.sql

echo "TRADES_EQUITY_CURVE_VIEWS_TEST_OK"
