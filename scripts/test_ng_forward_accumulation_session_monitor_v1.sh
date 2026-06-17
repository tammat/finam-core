#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== NG FORWARD ACCUMULATION SESSION MONITOR V1 ==="
echo "mode=diagnostic"
echo "runtime_allow=0"
echo "execution_enabled=0"

echo
echo "=== 1. SERVICE STATUS ==="
systemctl is-active finam-paper-pipeline.service || true

echo
echo "=== 2. NG RECENT BARS ==="
psql "$DATABASE_URL" -c "
select
    symbol,
    timeframe,
    count(*) bars,
    max(ts) last_bar
from market_bars
where symbol in ('NGM6@RTSX','NGQ6@RTSX')
  and timeframe in ('M1','M5')
group by 1,2
order by symbol,timeframe;
"

echo
echo "=== 3. NG RECENT TRADES 24H ==="
psql "$DATABASE_URL" -c "
select
    symbol,
    strategy,
    timeframe,
    side,
    count(*) trades,
    min(created_at) first_trade,
    max(created_at) last_trade
from trades
where symbol in ('NGM6@RTSX','NGQ6@RTSX')
  and strategy in ('NG_CONSERVATIVE_BREAKOUT','NG_CONSERVATIVE_BREAKOUT_M1')
  and created_at >= now() - interval '24 hours'
group by 1,2,3,4
order by symbol,strategy,timeframe,side;
"

echo
echo "=== 4. NG PIPELINE LOGS 60M ==="
journalctl -u finam-paper-pipeline.service --since "60 minutes ago" --no-pager | \
grep -E "NGM6@RTSX|NGQ6@RTSX|PIPE_SMART_ENTRY|NG_PAPER|PaperExecution|FILL|TRADE|PIPE_RISK_OK" | \
tail -120 || true

echo
echo "=== 5. CLEAN V3 SNAPSHOT ==="
psql "$DATABASE_URL" -c "
select
    symbol,
    strategy,
    timeframe,
    clean_trades,
    trade_days,
    v3_full_chains,
    round(v3_net_pnl,6) as pnl,
    round(v3_net_pnl / nullif(v3_full_chains,0),6) as expectancy,
    accumulation_status
from clean_paper_accumulation_tracker_v1
where symbol in ('NGM6@RTSX','NGQ6@RTSX')
order by expectancy desc nulls last;
"

echo "NG_FORWARD_ACCUMULATION_SESSION_MONITOR_V1_OK"
