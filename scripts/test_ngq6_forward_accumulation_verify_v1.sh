#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== NGQ6 FORWARD ACCUMULATION VERIFY V1 ==="
echo "mode=diagnostic"
echo "runtime_allow=0"
echo "execution_enabled=0"

echo
echo "=== 1. RUNTIME ACTIVE UNIVERSE ==="
psql "$DATABASE_URL" -c "
select
    symbol,
    strategy,
    timeframe,
    priority,
    is_enabled,
    source,
    updated_at
from runtime_active_universe
where symbol='NGQ6@RTSX'
order by strategy,timeframe;
"

echo
echo "=== 2. SERVICE STATUS ==="
systemctl is-active finam-paper-pipeline.service || true

echo
echo "=== 3. RECENT NGQ6 BARS ==="
psql "$DATABASE_URL" -c "
select
    symbol,
    timeframe,
    count(*) bars,
    max(ts) last_bar
from market_bars
where symbol='NGQ6@RTSX'
  and timeframe in ('M1','M5','H1')
group by 1,2
order by timeframe;
"

echo
echo "=== 4. RECENT NGQ6 LOGS ==="
journalctl -u finam-paper-pipeline.service --since "30 minutes ago" --no-pager | \
grep -E "NGQ6@RTSX|NG_CONSERVATIVE_BREAKOUT_M1|PIPE_NG|NG_PAPER|PIPE_SMART_ENTRY|PIPE_RISK_OK|PaperExecution|FILL|TRADE" | \
tail -160 || true

echo
echo "=== 5. RECENT NGQ6 TRADES ==="
psql "$DATABASE_URL" -c "
select
    created_at,
    symbol,
    strategy,
    timeframe,
    side,
    origin,
    trade_source,
    qty,
    price
from trades
where symbol='NGQ6@RTSX'
  and created_at >= now() - interval '24 hours'
order by created_at desc
limit 30;
"

echo
echo "=== 6. CURRENT CLEAN V3 NGQ6 ==="
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
where symbol='NGQ6@RTSX'
order by strategy,timeframe;
"

echo "NGQ6_FORWARD_ACCUMULATION_VERIFY_V1_OK"
