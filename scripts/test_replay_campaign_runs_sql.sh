#!/usr/bin/env bash
set -euo pipefail

psql "$DATABASE_URL" -f sql/create_replay_campaign_runs.sql >/dev/null

psql "$DATABASE_URL" -c "
select
  column_name
from information_schema.columns
where table_name = 'replay_campaign_runs'
  and column_name in (
    'campaign_id',
    'symbol',
    'window_index',
    'signals',
    'paper_orders',
    'trades_logged',
    'closed_trades',
    'net_pnl',
    'winrate'
  )
order by column_name;
"

echo "REPLAY_CAMPAIGN_RUNS_SQL_OK"
