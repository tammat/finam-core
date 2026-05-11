#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

test -f sql/20260511_trades_paired_pnl_summary.sql

grep -q "v_trades_pnl_paired_summary_grafana" sql/20260511_trades_paired_pnl_summary.sql
grep -q "Winrate %" sql/20260511_trades_paired_pnl_summary.sql
grep -q "Realized P&L" sql/20260511_trades_paired_pnl_summary.sql
grep -q "Худшая сделка" sql/20260511_trades_paired_pnl_summary.sql
grep -q "Лучшая сделка" sql/20260511_trades_paired_pnl_summary.sql

echo "TRADES_PAIRED_PNL_SUMMARY_TEST_OK"
