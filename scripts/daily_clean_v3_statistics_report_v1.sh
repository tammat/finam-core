#!/usr/bin/env bash
set -euo pipefail

REPORT_DATE="${1:-$(date -d yesterday +%F)}"

echo "=== DAILY CLEAN V3 STATISTICS REPORT V1 ==="
echo "date=${REPORT_DATE}"
echo "runtime_allow=0"
echo "execution_enabled=0"
echo

echo "=== 1. DAILY PNL BY STRATEGY ==="
psql "$DATABASE_URL" -c "
select
    symbol,
    strategy,
    timeframe,
    count(*) as trades,
    round(sum(net_pnl),6) as pnl,
    round(avg(net_pnl),6) as expectancy,
    round(
        100.0 * count(*) filter (where net_pnl > 0) / nullif(count(*),0),
        2
    ) as winrate_pct
from closed_trade_chains_v3
where entry_ts::date = '${REPORT_DATE}'
group by symbol, strategy, timeframe
order by pnl desc;
"

echo
echo "=== 2. DAILY PNL BY HOUR MSK ==="
psql "$DATABASE_URL" -c "
select
    symbol,
    strategy,
    extract(hour from entry_ts at time zone 'Europe/Moscow')::int as hour_msk,
    count(*) as trades,
    round(sum(net_pnl),6) as pnl,
    round(avg(net_pnl),6) as expectancy
from closed_trade_chains_v3
where entry_ts::date = '${REPORT_DATE}'
group by symbol, strategy, hour_msk
order by symbol, hour_msk;
"

echo
echo "=== 3. WORST TRADES ==="
psql "$DATABASE_URL" -c "
select
    symbol,
    strategy,
    entry_ts,
    exit_ts,
    side,
    entry_price,
    exit_price,
    round(net_pnl,6) as pnl
from closed_trade_chains_v3
where entry_ts::date = '${REPORT_DATE}'
order by net_pnl asc
limit 20;
"

echo
echo "=== 4. BEST TRADES ==="
psql "$DATABASE_URL" -c "
select
    symbol,
    strategy,
    entry_ts,
    exit_ts,
    side,
    entry_price,
    exit_price,
    round(net_pnl,6) as pnl
from closed_trade_chains_v3
where entry_ts::date = '${REPORT_DATE}'
order by net_pnl desc
limit 20;
"

echo
echo "=== 5. CURRENT CLEAN V3 ACCUMULATION ==="
psql "$DATABASE_URL" -c "
select
    symbol,
    strategy,
    timeframe,
    clean_trades,
    trade_days,
    v3_full_chains,
    v3_partial_chains,
    round(v3_net_pnl,6) as pnl,
    accumulation_status,
    accumulation_reason
from clean_paper_accumulation_tracker_v1
order by v3_net_pnl desc;
"

echo
echo "DAILY_CLEAN_V3_STATISTICS_REPORT_V1_OK"
