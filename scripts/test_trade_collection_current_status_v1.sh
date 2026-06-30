#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_TRADE_COLLECTION_CURRENT_STATUS_V1 ==="

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'trades_total=' || count(*) FROM public.trades;

SELECT 'closed_trades_total=' || count(*) FROM public.closed_trades;

SELECT 'fills_total=' || count(*) FROM public.fills;

SELECT 'latest_trade=' || coalesce(max(created_at)::text,'NULL') FROM public.trades;

SELECT 'latest_closed_trade=' || coalesce(max(exit_ts)::text,'NULL') FROM public.closed_trades;

SELECT 'latest_fill=' || coalesce(max(created_at)::text,'NULL') FROM public.fills;

SELECT 'today_trades=' || count(*) FROM public.trades WHERE created_at::date = current_date;

SELECT 'today_closed_trades=' || count(*) FROM public.closed_trades WHERE exit_ts::date = current_date;

SELECT 'today_fills=' || count(*) FROM public.fills WHERE created_at::date = current_date;

SELECT 'VERDICT=TRADE_COLLECTION_CURRENT_STATUS_READY';
SQL

echo "TEST_TRADE_COLLECTION_CURRENT_STATUS_V1_OK"
