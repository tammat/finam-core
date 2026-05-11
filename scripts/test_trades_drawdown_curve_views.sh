#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

test -f sql/20260511_trades_drawdown_curve_views.sql

grep -q "v_trades_drawdown_curve_ui" sql/20260511_trades_drawdown_curve_views.sql
grep -q "v_trades_drawdown_curve_grafana" sql/20260511_trades_drawdown_curve_views.sql
grep -q "Peak Equity P&L" sql/20260511_trades_drawdown_curve_views.sql
grep -q "Drawdown %" sql/20260511_trades_drawdown_curve_views.sql
grep -q "ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW" sql/20260511_trades_drawdown_curve_views.sql
grep -q "ts AS time" sql/20260511_trades_drawdown_curve_views.sql

echo "TRADES_DRAWDOWN_CURVE_VIEWS_TEST_OK"
