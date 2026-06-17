#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== USDRUBF PAPER SIGNAL FLOW AUDIT V1 ==="
echo "mode=diagnostic"
echo "runtime_allow=0"
echo "execution_enabled=0"

echo "STEP_1_BARS_FRESHNESS"
psql "$DATABASE_URL" -c "
select
    symbol,
    timeframe,
    count(*) bars,
    min(ts) first_bar,
    max(ts) last_bar
from market_bars
where symbol='USDRUBF@RTSX'
group by 1,2
order by max(ts) desc;
"

echo "STEP_2_TRADES_BY_DAY"
psql "$DATABASE_URL" -c "
select
    created_at::date trade_date,
    side,
    origin,
    coalesce(strategy,'') strategy,
    coalesce(timeframe,'') timeframe,
    count(*) cnt,
    min(created_at) first_ts,
    max(created_at) last_ts
from trades
where symbol='USDRUBF@RTSX'
group by 1,2,3,4,5
order by 1,2,3,4,5;
"

echo "STEP_3_RECENT_USD_PIPELINE_LOGS"
journalctl -u finam-paper-pipeline.service --since "12 hours ago" --no-pager | \
grep -Ei "USDRUBF|USD_INTRADAY|USD_PAPER|PIPE_USD|PIPE_SMART_ENTRY|PIPE_BREAKOUT_DETECTED|PIPE_EDGE_GATE_STRICT_MODE|PIPE_RUNTIME_EDGE_GOVERNANCE_PHASE2|PIPE_TREND_BLOCK|PaperExecution|FILL|TRADE" | \
tail -200 || true

echo "STEP_4_RECENT_USD_TRADE_COUNT"
recent_trades=$(psql "$DATABASE_URL" -At -c "
select count(*)
from trades
where symbol='USDRUBF@RTSX'
  and created_at >= now() - interval '12 hours';
")
echo "recent_usdrubf_trades_12h=${recent_trades}"

echo "USDRUBF_PAPER_SIGNAL_FLOW_AUDIT_V1_OK"
