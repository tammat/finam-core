#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

test -f sql/20260511_trades_drawdown_summary.sql

grep -q "v_trades_drawdown_summary_grafana" sql/20260511_trades_drawdown_summary.sql
grep -q "Max Drawdown" sql/20260511_trades_drawdown_summary.sql
grep -q "Current Equity P&L" sql/20260511_trades_drawdown_summary.sql

echo "TRADES_DRAWDOWN_SUMMARY_TEST_OK"
