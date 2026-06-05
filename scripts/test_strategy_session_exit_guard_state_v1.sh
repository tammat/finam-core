#!/usr/bin/env bash
set -euo pipefail

python3 -m py_compile src/scripts/analytics/materialize_strategy_session_exit_guard_state_v1.py

python3 src/scripts/analytics/materialize_strategy_session_exit_guard_state_v1.py \
  --symbols NGN6@RTSX,BRN6@RTSX \
  --min-stop-trades 3

python3 src/scripts/analytics/materialize_strategy_session_exit_guard_state_v1.py \
  --symbols NGN6@RTSX,BRN6@RTSX \
  --min-stop-trades 3 \
  --apply

psql "$DATABASE_URL" -c "
select
  symbol,
  strategy,
  timeframe,
  side,
  session_bucket,
  decision,
  total_trades,
  stop_trades,
  stop_net_pnl,
  take_trades,
  take_net_pnl
from strategy_session_exit_guard_state
where symbol in ('NGN6@RTSX','BRN6@RTSX')
order by
  case decision
    when 'BLOCK_STOP_DOMINATED' then 0
    when 'WATCH_NEGATIVE_TOTAL' then 1
    else 2
  end,
  stop_net_pnl asc;
"
